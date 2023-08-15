import chess, chess.engine

from engine_engine import *
import engine_utils as utils
from engine_search_h import *
from engine_ucioption import *
from engine_timeman import *
import engine_tt as tt
from engine_zobrist import Zobrist as Zo

from time import time as time_now
import threading
import math

STOP_SEARCH = OPTTIME = MAXTIME = False
NODES = 0
default_nodes = option("Nodes")

ttTable = tt.TranspositionTable(size=option("Hash"))

PV = []

# Objects
Z = Zo()
last_output = time_now()

def search(pos: chess.Board, depth: int, alpha: Value, beta: Value, 
           PvNode: bool = False, rootNode: bool = False):
    """
    Good, old-fashioned alpha-beta search.
    """
    global NODES, ttTable, PV, last_output

    NODES += 1

    if (depth <= 0):
        return evaluate(pos, default_nodes)
    
    # Init
    PvNode = rootNode or PvNode  # rootNode is PV

    ttEntry = ttTable.get(pos)
    ttHit: bool = not ttEntry.is_none()
    ttValue = ttEntry.value if ttHit else None
    ttEval = ttEntry.eval if ttHit else None
    ttDepth = ttEntry.depth if ttHit else 0
    ttMove = ttEntry.move if ttHit else None

    posKey = Z.hash(pos)

    staticEval = Eval = None
    if ttHit:
        staticEval = Eval = ttEval
        if staticEval is None:
            staticEval = Eval = evaluate(pos, default_nodes)
        
        # ttValue can be used as a better position evaluation
        if ttValue is not None:
            Eval = ttValue
    
    else:
        staticEval = Eval = evaluate(pos, default_nodes)
        # Save staticEval to tt
        tte = ttTable.TTEntry(posKey, move=None, value=None, eval=staticEval, depth=0)
        ttTable.save(posKey, tte)
    
    bestValue = -VALUE_INFINITE
    bestMove = None

    # Moves loop
    moveCount = 0
    for move in pos.legal_moves:
        moveCount += 1

        if rootNode:
            # currmove output
            elapsed = int( (time_now() - last_output) * 1000 )
            if elapsed >= 3000:
                nps = int( NODES / (elapsed / 1000) )
                print(f"info currmove {move} currmovenumber {moveCount} nps {nps}")
                last_output = time_now()

        # Extensions
        extension = 0
        if ttHit and move == ttMove and depth >= 4 and ttDepth >= depth - 3:
            singularBeta = ttValue - 2 * depth
            value = search(pos, (depth - 1) // 2, singularBeta-1, singularBeta, False)
            if value < singularBeta:
                extension = 1
                if (not PvNode and value <= singularBeta - 20):
                    extension = 2

            if ttValue >= beta:
                extension = -2
            elif ttValue <= value:
                extension = -1
            elif depth > 6 and Eval - 100:
                extension = -1
        else:
            # Check extensions
            if pos.gives_check(move) and depth >= 8:
                extension = 1
        
        newDepth = depth + extension

        # Make the move
        pos.push(move)

        # Reductions
        r = 0
        if PvNode: r -= 1
        if move == ttMove: r += 1

        # LMR
        d = clamp(newDepth - r, 1, newDepth+1)
        value = -search(pos, d, -(alpha+1), -alpha, False)

        # TODO: Do a full-depth search when reduced LMR search fails high

        # For PV nodes only, do a full PV search on the first move
        # or after a fail high (in the latter case search only if value < beta)
        if PvNode and value > alpha and (rootNode or value < beta):
            value = -search(pos, newDepth, -beta, -alpha, True)

        # Undo move
        pos.pop()

        if value > bestValue:
            bestValue = value

            if value > alpha:
                bestMove = move
                if PvNode and not rootNode:
                    # TODO: Update PV
                    pass
                if value >= beta:
                    # Fail high
                    break
                else:
                    alpha = value

    # End of moves loop

    # Write gathered information in transposition table
    tte = ttTable.TTEntry(posKey, move=bestMove, value=bestValue, eval=Eval, depth=depth)
    ttTable.save(posKey, tte)

    if rootNode:
        PV += [bestMove]

    return bestValue
    

def search_main(rootPos: chess.Board, MAX_MOVES=5, MAX_ITERS=5, depth: int = None, nodes: int = None, movetime: int = None,
           mate: int = None, timeman: Time = Time()):
    global STOP_SEARCH, lastNps
    global OPTTIME, MAXTIME
    global NODES, PV, ttTable, last_output
    global default_nodes

    default_nodes = option("Nodes")
    NODES = 0
    PV = []
    ttTable = tt.TranspositionTable(option("Hash"))
    
    if depth is None:
        depth = MAX_DEPTH

    # initialise timeman object
    timeman.init(rootPos.turn, rootPos.ply())
    optTime = timeman.optTime
    maxTime = timeman.maxTime
    if movetime:
        optTime = maxTime = movetime

    startTime = time_now()
    optTime_timer = maxTime_timer = None
    
    # Set timer
    if optTime:
        optTime_timer = threading.Timer(optTime / 1000, stop_search, args=(True, False))
        optTime_timer.start()
        if option("debug"):
            print(f"info string Timeman: Optimal time {optTime}ms")
    if maxTime:
        maxTime_timer = threading.Timer(maxTime / 1000, stop_search, args=(True, True))
        maxTime_timer.start()
    
    alpha = -VALUE_INFINITE
    beta = VALUE_INFINITE

    for rootDepth in range(1, depth):
        bestValue = search(rootPos, rootDepth, alpha, beta, True, True)
        if bestValue <= alpha:
            beta = (alpha + beta) // 2
            alpha = max(bestValue - 10, -VALUE_INFINITE)
        elif bestValue >= beta:
            beta = min(bestValue + 10, VALUE_INFINITE)
        elapsed = max( int( (time_now() - startTime) * 1000 ), 1 )
        nps = int( NODES / (elapsed / 1000) )
        
        print(f"info depth {rootDepth} score cp {bestValue} nodes {NODES}\
               nps {nps} time {elapsed} pv {PV}")
        last_output = time_now()


def stop_search(optTime=False, maxTime=False):
    global STOP_SEARCH, OPTTIME, MAXTIME
    STOP_SEARCH = True
    
    if optTime:
        OPTTIME = True
    if maxTime:
        MAXTIME = True
