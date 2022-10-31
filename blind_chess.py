import logging
from time import time
from typing import Union

from stockfish import Stockfish

WAIT_CORRECT_POSITION = 1
WAIT_HUMAN_MOVE = 2
WAIT_HUMAN_TAKE = 3
GAME_MOVE = 4
GAME_PC_MOVE = 5
WAIT_PC_MOVE_ON_BOARD = 6
GAME_PROMOTION_REQUEST = 7
GAME_PROMOTION = 8
GAME_CHECKMATE = 9

PROMOTION_PIECES = ('R', 'N', 'B', 'Q')

# While a player is moving a piece around the board
# the piece may not be in its final position.
# The engine has to wait until the piece becomes
# motionless during this time
SLIDING_TIME_SEC = 0.3


class ChessGame:
    chess_engine = None

    # Time when external position was changed
    _position_changed_at = 0

    # Set of occupied squares on the internal board {'h8', 'b7', 'h7', ...}
    _internal_position = set()
    # Set of occupied squares on the external board
    _external_position = set()

    _promotion_piece = ''

    game_situation = WAIT_CORRECT_POSITION

    last_pc_movement = ''
    taking_movement = ''

    last_response = {'diff': '', 'action': WAIT_CORRECT_POSITION, 'board': ''}
    last_external_position = set()
    
    def __init__(self, stockfish_path: str = None, fen_position: str = None):
        kwargs = {'path': stockfish_path} if stockfish_path else {}
        self.chess_engine = Stockfish(**kwargs)
        self.set_initial_position(fen_position)

    @staticmethod
    def _sort_diff(diff: str) -> str:
        """
        :param diff: squares string  ('d7a2a1d8')
        :return: sorted squares ('a1a2d7d8')
        """
        return ''.join(sorted([diff[i:i + 2] for i in range(0, len(diff), 2)]))

    def _make_external_position(self) -> set:
        """
        Convert current fen position into set of squares
        :return: {'a5', 'b7', 'h3'}
        """
        pos_str = self.chess_engine.get_fen_position().split(' ')[0].replace('/', '')
        pos_list = []
        i = 0
        for s in pos_str:
            if s.isdigit():
                i += int(s)
            else:
                pos_list.append('abcdefgh'[i % 8] + str(8 - i // 8))
                i += 1
        return set(pos_list)

    def set_initial_position(self, fen_position: str = None):
        """
        :param fen_position: start fen position
        """
        if not fen_position:
            fen_position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        self.chess_engine.set_fen_position(fen_position)

        self._internal_position.clear()
        self._internal_position.update(self._make_external_position())
        self.game_situation = WAIT_CORRECT_POSITION

    def process(self, position: Union[set, list]) -> dict:
        """
        :param position: set of occupied squares
        :return: diff/action/board
        """
        while True:
            resp = {
                'diff': '',
            }
            now = time()
            self.last_external_position = external_position = set(position)
            if self._external_position != external_position:
                self._external_position = external_position
                self._position_changed_at = now
                logging.info(f'new external position: {external_position}')
                if self.game_situation == WAIT_PC_MOVE_ON_BOARD:
                    self.game_situation = WAIT_CORRECT_POSITION

            if self.game_situation == GAME_PC_MOVE:
                movement = self.make_pc_move()
                if movement is None:
                    self.game_situation = GAME_CHECKMATE
                    break
                resp['diff'] = movement
                self.game_situation = WAIT_PC_MOVE_ON_BOARD
                break

            diff = (
               (external_position - self._internal_position) |
               (self._internal_position - external_position)
            )

            diff_as_str = self._sort_diff(''.join(diff))

            if self.game_situation == WAIT_PC_MOVE_ON_BOARD:
                if diff:
                    resp['diff'] = self.last_pc_movement
                else:
                    self.game_situation = WAIT_HUMAN_MOVE
                break

            if self.game_situation == WAIT_CORRECT_POSITION:
                if diff:
                    resp['diff'] = diff_as_str
                else:
                    self.game_situation = WAIT_HUMAN_MOVE
                break

            if self.game_situation in (WAIT_HUMAN_MOVE, WAIT_HUMAN_TAKE, GAME_PROMOTION):
                if not diff:
                    break

                movement = None

                # how many pieces have been removed from the board
                # if piece_count_diff < 0: extra pieces are on the board
                piece_count_diff = len(self._internal_position) - len(external_position)

                if piece_count_diff not in (0, 1, 2):
                    # an extra piece appeared or more than 2 piece are taken from the board
                    logging.info('incorrect position')
                    resp['diff'] = diff_as_str
                    self.game_situation = WAIT_CORRECT_POSITION
                    break

                # 2 piece are taken from the board - taking movement
                if piece_count_diff == 2:
                    if self.game_situation == WAIT_HUMAN_MOVE:
                        self.taking_movement = list(self._internal_position - external_position)[0:2]
                        logging.info(f'first part of taking movement: {self.taking_movement}')
                    self.game_situation = WAIT_HUMAN_TAKE
                    break

                # position has been changed and all pieces on the board - piece moving
                if (
                    self.game_situation in (WAIT_HUMAN_MOVE, GAME_PROMOTION) and
                    not piece_count_diff
                ):
                    # wait piece fixation on the board after sliding
                    if (now - self._position_changed_at) < SLIDING_TIME_SEC:
                        logging.info('piece fixation waiting')
                        break
                    # if len(diff) == 2 - only one piece is moved
                    if len(diff) != 2:
                        # castling?
                        if diff_as_str == 'e1f1g1h1':
                            # temporarily return the rook to its place
                            external_position -= {'f1'}
                            external_position.add('h1')
                        elif diff_as_str == 'a1c1d1e1':
                            external_position -= {'d1'}
                            external_position.add('a1')
                        else:
                            logging.info('incorrect position 2')
                            resp['diff'] = diff_as_str
                            self.game_situation = WAIT_CORRECT_POSITION
                            break
                    movement = (
                        list(self._internal_position - external_position)[0] +
                        list(external_position - self._internal_position)[0]
                    )

                    if self.game_situation == GAME_PROMOTION:
                        pr_movement = f'{movement}{self._promotion_piece}'
                        if not self.chess_engine.is_move_correct(pr_movement):
                            logging.info('movement incorrect')
                            self.game_situation = WAIT_CORRECT_POSITION
                            break
                        self.chess_engine.make_moves_from_current_position([pr_movement])
                        self.game_situation = GAME_PC_MOVE
                        resp['diff'] = ''
                        break

                    logging.info(f'movement: {movement}')
                    self.game_situation = GAME_MOVE

                if self.game_situation == WAIT_HUMAN_TAKE and piece_count_diff == 1:
                    movement = list(self._internal_position - external_position)[0]
                    t_m = self.taking_movement
                    movement += t_m[1] if movement == t_m[0] else t_m[0]
                    logging.info(f'taking: {movement}')
                    self.game_situation = GAME_MOVE

                if self.game_situation != GAME_MOVE:
                    break

                if not self.chess_engine.is_move_correct(movement):
                    if self.chess_engine.is_move_correct(f'{movement}Q'):
                        self.game_situation = GAME_PROMOTION_REQUEST
                        break
                    logging.info('movement incorrect')
                    resp['diff'] = diff_as_str
                    self.game_situation = WAIT_CORRECT_POSITION
                    break

                self.chess_engine.make_moves_from_current_position([movement])
                resp['diff'] = ''
                self.game_situation = GAME_PC_MOVE
                break

            break

        resp['board'] = self.chess_engine.get_fen_position().split(' ')[0].replace('/', '')
        resp['action'] = self.game_situation

        self.last_response = resp
        return resp

    def make_pc_move(self):
        pc_movement = self.last_pc_movement = self.chess_engine.get_best_move()
        if pc_movement is None:
            return None
        logging.info(f'pc movement: {pc_movement}')
        self.chess_engine.make_moves_from_current_position([pc_movement])
        self._internal_position = self._make_external_position()
        return self._sort_diff(pc_movement)

    def promotion(self, piece: str):
        if piece in PROMOTION_PIECES:
            self._promotion_piece = piece
            self.game_situation = GAME_PROMOTION
