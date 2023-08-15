import random
import chess
from chess import Board
from engine_ucioption import *

class Zobrist:
    def __init__(self):
        self.pieces = [[0 for i in range(64)] for j in range(12)]
        for i in range(12):
            for j in range(64):
                self.pieces[i][j] = random.randint(0, 2 ** 64 - 1)
        self.side = random.randint(0, 2 ** 64 - 1)
        self.en_passant = [random.randint(0, 2 ** 64 - 1) for i in range(8)]
        self.castling = [random.randint(0, 2 ** 64 - 1) for i in range(16)]
    
    def hash(self, position: Board):
        h = 0
        for i in range(64):
            piece = position.piece_at(i)
            if piece is not None:
                h ^= self.pieces[piece.piece_type][i]
        if position.turn == chess.BLACK:
            h ^= self.side
        if position.ep_square is not None:
            h ^= self.en_passant[position.board.ep_square % 8]
        for i in range(16):
            if position.has_castling_rights(i):
                h ^= self.castling[i]
        return h % option("Hash")