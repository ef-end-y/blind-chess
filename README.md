# Blind chess
Blind chess is a layer between a chess device and a chess engine ([Stockfish](https://stockfishchess.org/)).

## Why blind?
Suppose you want to create a chess machine like [Mephisto](https://en.wikipedia.org/wiki/Mephisto_(chess_computer)). This chess machine can't see which piece is on which square. But the physical board knows which squares are occupied by pieces. Chess pieces have magnets and the chessboard has sensors which react on the magnetic field. So the device knows what square is occupied. 

When a person makes a move, he picks up a piece, the device registers that the square is free. When he puts the piece on the board in another position, the device registers movement of the piece.

Blind chess takes over the analysis of changes in occupied positions and converts this into moves understandable to Stockfish.

### Video
[![Blind chess video](https://img.youtube.com/vi/vfnmE8J7HIw/default.jpg)](https://www.youtube.com/shorts/vfnmE8J7HIw)

## Requirements
* Python 3.7+
* stockfish
* python stockfish

```shell
    pip install stockfish
    sudo apt install stockfish
```

## Example

```python
    from time import sleep
    import blind_chess

    game = blind_chess.ChessGame()
    # move e2-e4
    position = {
        # Let's say we got this position from magnetic sensors
        'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
        'a2', 'b2', 'c2', 'd2', 'e4', 'f2', 'g2', 'h2',
        'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
        'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
    }
    resp = game.process(position)
    # While a player is moving a piece around the board,
    # the piece may not be in its final position.
    # Blind chess waits until the piece becomes motionless
    sleep(blind_chess.SLIDING_TIME_SEC)
    resp = game.process(position)
    # Now Stockfish moves
    resp = game.process(position)
    print(resp['diff'])  # maybe e7-e5, who knows
```

A chess device periodically has to send a list (or set) of occupied squares. The response will be received:
- diff - what to do on the board
- action - current situation

It should be noted that making requests to blind chess is not only necessary when the position has been changed. Blind chess takes into account the time it takes to consider a piece fixed. Thus, periodically send the current position.

I recommend to do the following: make a request as soon as the position has been changed and repeat after SLIDING_TIME_SEC seconds. Then if the position will not be changed, then send it every 2 seconds.

## Situations
- Incorrect position (a person can make an incorrect move or chaotically place pieces)
- Moving a piece
- Taking a piece
- Castling
- A chess engine move
- Checkmate

If you play chess for example on chess.com you cannot make an incorrect move. If a player uses a physical board he can make not only incorrect moves. He can misplace pieces or remove some pieces from the board or add extra pieces.

That is why blind chess first of all makes sure the position corresponds to the real position of the game. In case of an incorrect position g.process() returns action = WAIT_CORRECT_POSITION, diff = list of error squares.

A square is error if:
- there should be a piece on its place
- there should not be a piece on its place

Mephisto in this case blinks LEDs and this shows where you need to put or pick up a piece.

```python
    # incorrect move e2-e5
    position = {
        'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
        'a2', 'b2', 'c2', 'd2', 'e5', 'f2', 'g2', 'h2',
        'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
        'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
    }
    resp = game.process(position)
    print(resp['action'])  # 1 (WAIT_CORRECT_POSITION)
    print(resp['diff'])  # 'e2e5'
```
