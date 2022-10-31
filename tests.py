import unittest
from time import sleep

import blind_chess as bc


SLIDING_TIME_SEC = bc.SLIDING_TIME_SEC + 0.01


class TestBlindChess(unittest.TestCase):
    def setUp(self):
        self.g = bc.ChessGame()

    def tearDown(self):
        stdout = self.g.chess_engine._stockfish.stdout
        stdin = self.g.chess_engine._stockfish.stdin
        del self.g.chess_engine
        stdout.close()
        stdin.close()

    def test_methods(self):
        g = self.g

        g.set_initial_position()
        self.assertEqual(
            g.chess_engine.get_fen_position(),
            'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        )

        fen = '8/PK6/5k2/8/8/8/8/8 w - - 0 1'
        g.set_initial_position(fen)
        self.assertEqual(g.chess_engine.get_fen_position(), fen)
        self.assertEqual(g._make_external_position(), {'a7', 'b7', 'f6'})

        self.assertEqual(g._sort_diff('c3c2c1b1b2a8a1'), 'a1a8b1b2c1c2c3')
        self.assertEqual(g._sort_diff(''), '')
        self.assertEqual(g._sort_diff('h5'), 'h5')

    def test_moving(self):
        g = self.g

        # position: black king A7, white king C7, white rook C6
        g.set_initial_position('8/k1K5/2R5/8/8/8/8/8 w - - 0 1')

        # correct position on the blind board
        self.assertDictEqual(
            g.process({'a7', 'c7', 'c6'}),
            {'diff': '', 'board': '8k1K52R588888', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # incorrect position but a player can move a piece now, and it is not in
        # final position yet. The engine waits SLIDING_TIME_SEC for piece fixation
        pos = {'a7', 'c7', 'd7'}
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': '8k1K52R588888', 'action': bc.WAIT_HUMAN_MOVE}
        )

        for _ in 0, 1:  # two iteration to check that the time will not affect the result
            sleep(bc.SLIDING_TIME_SEC)
            # incorrect position fixed
            self.assertDictEqual(
                g.process(pos),
                {'diff': 'c6d7', 'board': '8k1K52R588888', 'action': bc.WAIT_CORRECT_POSITION}
            )

        wait_move = {'diff': '', 'board': '8k1K52R588888', 'action': bc.WAIT_HUMAN_MOVE}
        # sliding rook c6 -> f6
        for pos in ('c6', 'd6', 'e6', 'f6'):
            sleep(bc.SLIDING_TIME_SEC / 2)
            self.assertDictEqual(g.process({'a7', 'c7', pos}), wait_move)

        # the rook is in a hand
        self.assertDictEqual(g.process({'a7', 'c7'}), wait_move)

        # the rook is in a hand for long time
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(g.process({'a7', 'c7'}), wait_move)

        # move is made but the engine waits piece fixation
        pos = {'a7', 'c7', 'h6'}
        self.assertDictEqual(g.process(pos), wait_move)

        sleep(SLIDING_TIME_SEC)
        # move is accepted
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': '8k1K57R88888', 'action': bc.GAME_PC_MOVE}
        )

        # black king has only one move
        for _ in 0, 1:
            self.assertDictEqual(
                g.process(pos),
                {'diff': 'a7a8', 'board': 'k72K57R88888', 'action': bc.WAIT_PC_MOVE_ON_BOARD}
            )

        for _ in 0, 1, 1:
            sleep(_ * bc.SLIDING_TIME_SEC / 3)
            self.assertDictEqual(
                g.process({'a8', 'c7', 'h6'}),
                {'diff': '', 'board': 'k72K57R88888', 'action': bc.WAIT_HUMAN_MOVE}
            )

    def test_taking(self):
        g = self.g

        """
        +---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |   | 8
        |   | p |   |   |   |   |   |   | 7
        |   |   |   |   |   |   |   |   | 6
        |   |   |   |   |   |   |   |   | 5
        |   |   |   |   |   |   |   |   | 4
        |   |   |   |   |   |   |   |   | 3
        |   | R | K |   |   |   |   |   | 2
        | k |   |   |   |   |   |   |   | 1
        +---+---+---+---+---+---+---+---+
          a   b   c   d   e   f   g   h
        """
        fen = '8/1p6/8/8/8/8/1RK5/k7 w - - 0 1'
        g.set_initial_position(fen)

        self.assertDictEqual(
            g.process({'a1', 'b2', 'b7', 'c2'}),
            {'diff': '', 'board': '81p688881RK5k7', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # take white rook in a hand
        for _ in 0, 0, 0, 1, 1, 0:
            sleep(_ * bc.SLIDING_TIME_SEC)
            self.assertDictEqual(
                g.process({'a1', 'b7', 'c2'}),
                {'diff': '', 'board': '81p688881RK5k7', 'action': bc.WAIT_HUMAN_MOVE}
            )

        # take black pawn in a hand
        for _ in 0, 1, 1, 1, 0:
            sleep(_ * bc.SLIDING_TIME_SEC / 3 + 0.01)
            self.assertDictEqual(
                g.process({'a1', 'c2'}),
                {'diff': '', 'board': '81p688881RK5k7', 'action': bc.WAIT_HUMAN_TAKE}
            )

        # put the rook on the white pawn place
        self.assertDictEqual(
            g.process({'a1', 'b7', 'c2'}),
            {'diff': '', 'board': '81R688882K5k7', 'action': bc.GAME_PC_MOVE}
        )

        # stockfish responds a1-a2
        for _ in 0, 1, 1, 1, 0:
            sleep(_ * bc.SLIDING_TIME_SEC/3 + 0.01)
            self.assertDictEqual(
                g.process({'a1', 'b7', 'c2'}),
                {'diff': 'a1a2', 'board': '81R68888k1K58', 'action': bc.WAIT_PC_MOVE_ON_BOARD}
            )

        # take black king in a hand
        for _ in 0, 1, 1, 1, 0:
            sleep(_ * bc.SLIDING_TIME_SEC/3 + 0.01)
            self.assertDictEqual(
                g.process({'b7', 'c2'}),
                {'diff': 'a2', 'board': '81R68888k1K58', 'action': bc.WAIT_CORRECT_POSITION}
            )

        # put black king on a2
        for _ in 0, 1, 1, 1, 0:
            sleep(_ * bc.SLIDING_TIME_SEC/3 + 0.01)
            self.assertDictEqual(
                g.process({'a2', 'b7', 'c2'}),
                {'diff': '', 'board': '81R68888k1K58', 'action': bc.WAIT_HUMAN_MOVE}
            )

        # --- the quickest player ---

        g.set_initial_position(fen)

        self.assertDictEqual(
            g.process({'a1', 'b2', 'b7', 'c2'}),
            {'diff': '', 'board': '81p688881RK5k7', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # take the rook and the pawn in hands
        self.assertDictEqual(
            g.process({'a1', 'c2'}),
            {'diff': '', 'board': '81p688881RK5k7', 'action': bc.WAIT_HUMAN_TAKE}
        )

        # put the rook
        self.assertDictEqual(
            g.process({'a1', 'b7', 'c2'}),
            {'diff': '', 'board': '81R688882K5k7', 'action': bc.GAME_PC_MOVE}
        )

        self.assertDictEqual(
            g.process({'a1', 'b7', 'c2'}),
            {'diff': 'a1a2', 'board': '81R68888k1K58', 'action': bc.WAIT_PC_MOVE_ON_BOARD}
        )

        # move the king
        self.assertDictEqual(
            g.process({'a2', 'b7', 'c2'}),
            {'diff': '', 'board': '81R68888k1K58', 'action': bc.WAIT_HUMAN_MOVE}
        )

    def test_errors(self):
        g = self.g

        # position: black king A7, white king C7, white rook C6
        g.set_initial_position('8/k1K5/2R5/8/8/8/8/8 w - - 0 1')

        self.assertDictEqual(
            g.process(set()),
            {'diff': 'a7c6c7', 'board': '8k1K52R588888', 'action': bc.WAIT_CORRECT_POSITION}
        )

        self.assertDictEqual(
            g.process({'a1'}),
            {'diff': 'a1a7c6c7', 'board': '8k1K52R588888', 'action': bc.WAIT_CORRECT_POSITION}
        )

        self.assertDictEqual(
            g.process({'a8', 'a7', 'c6', 'c7'}),
            {'diff': 'a8', 'board': '8k1K52R588888', 'action': bc.WAIT_CORRECT_POSITION}
        )

        self.assertDictEqual(
            g.process({'a7', 'c6', 'c7'}),
            {'diff': '', 'board': '8k1K52R588888', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # incorrect position after correct one
        pos = {'a1', 'a2', 'a3'}
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': '8k1K52R588888', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'a1a2a3a7c6c7', 'board': '8k1K52R588888', 'action': bc.WAIT_CORRECT_POSITION}
        )

    def test_errors2(self):
        g = self.g
        g.set_initial_position()

        pos = {
            'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
            'a2', 'b2', 'c2', 'd2', 'e2', 'f2', 'g2', 'h2',
            'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
            'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
        }
        board = 'rnbqkbnrpppppppp8888PPPPPPPPRNBQKBNR'
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': board, 'action': bc.WAIT_HUMAN_MOVE}
        )

        pos.add('e4')
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'e4', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )

        pos.add('e5')
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'e4e5', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )

        pos -= {'e4', 'e5', 'e1'}
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'e1', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )

        pos -= {'a1', 'a2', 'a7', 'a8', 'h1', 'h2', 'h7', 'h8'}
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'a1a2a7a8e1h1h2h7h8', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )
        pos.update({'e1', 'a1', 'a2', 'a7', 'a8', 'h1', 'h2', 'h7', 'h8'})
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': board, 'action': bc.WAIT_HUMAN_MOVE}
        )

        # e2 - e5
        pos -= {'e2'}
        pos.add('e5')
        g.process(pos)
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'e2e5', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )

        # change e2e5 -> e2e4
        pos -= {'e5'}
        pos.add('e4')
        # no. first make the position before the error (start position)
        self.assertDictEqual(
            g.process(pos),
            {'diff': 'e2e4', 'board': board, 'action': bc.WAIT_CORRECT_POSITION}
        )

        pos -= {'e4'}
        pos.add('e2')
        # start position
        self.assertDictEqual(
            g.process(pos),
            {'diff': '', 'board': board, 'action': bc.WAIT_HUMAN_MOVE}
        )

        # e2 - e4
        pos -= {'e2'}
        pos.add('e4')
        g.process(pos)
        sleep(SLIDING_TIME_SEC)
        resp = g.process(pos)
        self.assertEqual(resp['action'], bc.GAME_PC_MOVE)
        resp = g.process(pos)
        self.assertEqual(resp['action'], bc.WAIT_PC_MOVE_ON_BOARD)
        self.assertEqual(len(resp['diff']), 4)

    def test_castling(self):
        g = self.g

        # Position: black king A7, white king E1, white rook H1
        g.set_initial_position('8/k7/8/8/8/8/8/4K2R w KQ - 0 1')

        self.assertDictEqual(
            g.process({'a7', 'e1', 'h1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # take white king in a hand
        self.assertDictEqual(
            g.process({'a7', 'h1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC/10)
        # put white king
        self.assertDictEqual(
            g.process({'a7', 'g1', 'h1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # take white rook in a hand
        self.assertDictEqual(
            g.process({'a7', 'g1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # put white rook
        self.assertDictEqual(
            g.process({'a7', 'f1', 'g1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        # wait position fixation
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(
            g.process({'a7', 'f1', 'g1'}),
            {'diff': '', 'board': '8k7888885RK1', 'action': bc.GAME_PC_MOVE}
        )

    def test_castling2(self):
        g = self.g

        # Position: black king A7, white king E1, white rook H1
        g.set_initial_position('8/k7/8/8/8/8/8/4K2R w KQ - 0 1')

        self.assertDictEqual(
            g.process({'a7', 'e1', 'h1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # move white king
        self.assertDictEqual(
            g.process({'a7', 'g1', 'h1'}),
            {'diff': '', 'board': '8k7888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC)
        # Blind chess recognizes castling by moving the king
        self.assertDictEqual(
            g.process({'a7', 'g1', 'h1'}),
            {'diff': '', 'board': '8k7888885RK1', 'action': bc.GAME_PC_MOVE}
        )

    def test_castling3(self):
        g = self.g
        g.set_initial_position('4k2r/8/8/8/8/8/8/4K2R w KQkq - 0 1')

        self.assertDictEqual(
            g.process({'e8', 'h8', 'e1', 'h1'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )

        sleep(SLIDING_TIME_SEC/10)
        # move white king
        self.assertDictEqual(
            g.process({'e8', 'h8', 'f1', 'h1'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # move white king to the final position
        self.assertDictEqual(
            g.process({'e8', 'h8', 'g1', 'h1'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # move white rook
        self.assertDictEqual(
            g.process({'e8', 'h8', 'g1', 'h2'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # move white rook
        self.assertDictEqual(
            g.process({'e8', 'h8', 'g1', 'g2'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # move white rook
        self.assertDictEqual(
            g.process({'e8', 'h8', 'g1', 'f1'}),
            {'diff': '', 'board': '4k2r8888884K2R', 'action': bc.WAIT_HUMAN_MOVE}
        )
        # wait position fixation
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(
            g.process({'e8', 'h8', 'g1', 'f1'}),
            {'diff': '', 'board': '4k2r8888885RK1', 'action': bc.GAME_PC_MOVE}
        )

    def test_long_castling(self):
        g = self.g

        # Position: black king H8, white king E1, white rook a1
        g.set_initial_position('7k/8/8/8/8/8/8/R3K3 w KQ - 0 1')

        self.assertDictEqual(
            g.process({'h8', 'e1', 'a1'}),
            {'diff': '', 'board': '7k888888R3K3', 'action': bc.WAIT_HUMAN_MOVE}
        )

        # take white king in a hand
        self.assertDictEqual(
            g.process({'h8', 'a1'}),
            {'diff': '', 'board': '7k888888R3K3', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC/10)
        # put white king
        self.assertDictEqual(
            g.process({'h8', 'a1', 'c1'}),
            {'diff': '', 'board': '7k888888R3K3', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # take white rook in a hand
        self.assertDictEqual(
            g.process({'h8', 'c1'}),
            {'diff': '', 'board': '7k888888R3K3', 'action': bc.WAIT_HUMAN_MOVE}
        )
        sleep(SLIDING_TIME_SEC / 10)
        # put white rook
        self.assertDictEqual(
            g.process({'h8', 'c1', 'd1'}),
            {'diff': '', 'board': '7k888888R3K3', 'action': bc.WAIT_HUMAN_MOVE}
        )
        # wait position fixation
        sleep(SLIDING_TIME_SEC)
        self.assertDictEqual(
            g.process({'h8', 'c1', 'd1'}),
            {'diff': '', 'board': '7k8888882KR4', 'action': bc.GAME_PC_MOVE}
        )

    def test_promotion(self):
        g = self.g
        for promotion_piece in ('Q', 'N'):
            g.set_initial_position('8/PK6/5k2/8/8/8/8/8 w - - 0 1')
            g.process({'a7', 'b7', 'f6'})
            g.process({'a8', 'b7', 'f6'})
            sleep(SLIDING_TIME_SEC)
            for _ in 0, 1:
                self.assertDictEqual(
                    g.process({'a8', 'b7', 'f6'}),
                    {'diff': '', 'board': '8PK65k288888', 'action': bc.GAME_PROMOTION_REQUEST}
                )
            g.promotion(promotion_piece)
            self.assertDictEqual(
                g.process({'a8', 'b7', 'f6'}),
                {'diff': '', 'board': f'{promotion_piece}71K65k288888', 'action': bc.GAME_PC_MOVE}
            )


if __name__ == '__main__':
    unittest.main()
