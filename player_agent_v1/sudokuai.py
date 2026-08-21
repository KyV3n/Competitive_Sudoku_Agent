import random
import copy
import time
import competitive_sudoku.sudokuai
import math
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
from typing import List, Tuple, Optional, Iterator

Square = Tuple[int, int]

class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Competitive Sudoku AI using evaluation and minimax with alpha-beta pruning.
    """
    def __init__(self):
        super().__init__()

    def compute_best_move(self, game_state: GameState) -> None:
        """
        Compute the best move in a competitive sudoku game, given a certain game state.
        """
        # Initialize variables
        start_time = time.time()
        time_limit = 0.9                    # Time limit for computation

        N = game_state.board.N              # NxN board
        total_spaces = N * N
        empty_spaces = total_spaces - len(game_state.moves)
        # empty_spaces = total_spaces - len(game_state.moves) + len(game_state.taboo_moves)

        # Keep track of who your agent is playing as for the Minimax (whose perspective you measure from)
        my_agent_id = game_state.current_player

        # Maximum MiniMax search depth based on the number of empty spaces
        if empty_spaces > (total_spaces * 0.7):
            minimax_depth = 1
        elif empty_spaces > (total_spaces * 0.4):
            minimax_depth = 2
        elif empty_spaces > (total_spaces * 0.2):
            minimax_depth = 3
        else:
            minimax_depth = 4

        # Get all legal moves (square, value)
        all_moves = [Move((i, j), value)
                     for i in range(N)
                     for j in range(N)
                     for value in range(1, N+1)
                     if self.check_legal_move(i, j, value, game_state)]

        # If no legal moves, something is wrong
        if not all_moves:
            return

        # Propose a random move before starting the algorithm (prevent time-out without making a move)
        best_move = random.choice(all_moves)
        self.propose_move(best_move)

        # Initialize for minimax
        best_value = -math.inf

        # Minimax algorithm with alpha-beta pruning
        for move in all_moves:              # iterate over all legal moves
            candidate_square = move.square
            candidate_value = move.value

            # Time constraint
            if time.time() - start_time > time_limit:
                break  # Time limit exceeded

            # Make move and update board state
            move = Move(candidate_square, candidate_value)
            child_state = self.apply_move_search(game_state, move)

            # Search the branch (simulated future position) for an evaluation value
            candidate_value = self.minimax(child_state, depth=minimax_depth - 1, alpha=-math.inf, beta=math.inf, maximizing=False, start_time=start_time, time_limit=time_limit,
                                           my_agent_id=my_agent_id)

            if candidate_value > best_value:
                best_value = candidate_value
                best_move = move
                self.propose_move(best_move)

        if best_move is None:
            return

    def minimax(self, state: GameState, depth: int, alpha: float, beta: float, maximizing: bool, start_time: float,
                time_limit: float, my_agent_id: int) -> float:
        """
        Standard minimax algorithm with alpha-beta pruning.
        """
        # Stopping condition: Check for time limit
        if time.time() - start_time > time_limit:
            return self.evaluate_state(state, my_agent_id)

        # Stopping condition: Check for leaf node (depth reached)
        if depth == 0:
            return self.evaluate_state(state, my_agent_id)

        # Get all legal moves
        all_moves = [Move((i, j), value)
                     for i in range(state.board.N)
                     for j in range(state.board.N)
                     for value in range(1, state.board.N + 1)
                     if self.check_legal_move(i, j, value, state)]

        # Stopping condition: no legal moves
        if not all_moves:
            return self.evaluate_state(state, my_agent_id)

        # Random order for Minimax search
        random.shuffle(all_moves)

        # MAX player (1)
        if maximizing:
            value = -math.inf

            # Loop for all possible moves (branches) again
            for move in all_moves:
                if time.time() - start_time > time_limit:
                    break

                candidate_square = move.square
                candidate_value = move.value
                if candidate_value is None:
                    continue

                # Make move to new child state
                move = Move(candidate_square, candidate_value)
                child_state = self.apply_move_search(state, move)

                # Evaluate
                child_val = self.minimax(child_state, depth - 1, alpha, beta, False, start_time, time_limit, my_agent_id)
                value = max(value, child_val)

                # Pruning
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        # MIN player (2)
        else:
            value = math.inf

            # Loop for all possible moves (branches) again
            for move in all_moves:
                if time.time() - start_time > time_limit:
                    break

                candidate_square = move.square
                candidate_value = move.value
                if candidate_value is None:
                    continue

                # Make move to new child state
                move = Move(candidate_square, candidate_value)
                child_state = self.apply_move_search(state, move)

                # Evaluate
                child_val = self.minimax(child_state, depth - 1, alpha, beta, True, start_time, time_limit, my_agent_id)
                value = min(value, child_val)

                # Pruning
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    def clone_game_state(self, game_state: GameState) -> GameState:
        """Return a deep copy of the game state."""
        return copy.deepcopy(game_state)

    def apply_move_search(self, state: GameState, move: Move) -> GameState:
        """
        Simulate applying a move without modifying the original state (using a deep copy).
        """
        new_state = self.clone_game_state(state)            # Deep copy
        new_state.board.put(move.square, move.value)        # Make the move

        # Record the move in history
        new_state.moves.append(move)
        if new_state.current_player == 1:
            new_state.occupied_squares1.append(move.square)
        else:
            new_state.occupied_squares2.append(move.square)

        # Update scores for new move
        points = self.compute_local_score_for_move(new_state.board, move.square)
        new_state.scores[new_state.current_player - 1] += points

        # Switch player: 1 -> 2, 2 -> 1
        new_state.current_player = 3 - new_state.current_player

        return new_state

    def get_block_cells(self, board, square):
        """
        Return all coordinates belonging to the block containing square.
        """
        row, column = square

        block_height = board.region_height()
        block_width = board.region_width()

        start_row = (row // block_height) * block_height
        start_column = (column // block_width) * block_width

        for r in range(start_row, start_row + block_height):
            for c in range(start_column, start_column + block_width):
                yield (r, c)

    def compute_local_score_for_move(self, board, square):
        """
        Calculates the points scored for a particular move.
        This is based on whether the move completed a region (row, column or block).
            0 regions -> 0 points
            1 region  -> 1 point
            2 regions -> 3 points
            3 regions -> 7 points
        """
        row, column = square
        N = board.N
        EMPTY = SudokuBoard.empty

        completed = 0

        # Row scoring
        row_full = True
        for j in range(N):
            # Any cell in the move's row is still empty
            if board.get((row, j)) == EMPTY:
                row_full = False
                break
        if row_full:
            completed += 1

        # Column scoring
        col_full = True
        for i in range(N):
            # Any cell in the move's column is still empty
            if board.get((i, column)) == EMPTY:
                col_full = False
                break
        if col_full:
            completed += 1

        # Block scoring
        block_full = all(board.get(cell) != EMPTY for cell in self.get_block_cells(board, square))
        if block_full:
            completed += 1

        # Give score based on number of completed region's with the move
        if completed == 0:
            return 0
        elif completed == 1:
            return 1
        elif completed == 2:
            return 3
        elif completed == 3:
            return 7

    def check_block_square_value(self, row_idx: int, column_idx: int, value: int, game_state: GameState) -> bool:
        """
        Check if value already exists in the block containing (i, j).
        """
        square = (row_idx, column_idx)

        for row, column in self.get_block_cells(game_state.board, square):
            if game_state.board.get((row, column)) == value:
                return True

        return False

    def check_legal_move(self, row_idx: int, column_idx: int, value: int, game_state: GameState) -> bool:
        """
        Check if placing 'value' at square (row, column) is legal.
        """
        N = game_state.board.N

        # Check if the cell is empty
        if game_state.board.get((row_idx, column_idx)) != SudokuBoard.empty:
            return False

        # Check if it's a taboo move
        if TabooMove((row_idx, column_idx), value) in game_state.taboo_moves:
            return False

        # Check if the cell is within the allowed set of cells for the player
        if (row_idx, column_idx) not in game_state.player_squares():
            return False

        # Check row for value
        for col in range(N):
            if game_state.board.get((row_idx, col)) == value:
                return False

        # Check column for value
        for row in range(N):
            if game_state.board.get((row, column_idx)) == value:
                return False

        # Check block for value
        if self.check_block_square_value(row_idx, column_idx, value, game_state):
            return False

        return True     # legal move

    def evaluate_state(self, state: GameState, my_agent_id: int) -> float:
        """
        Evaluate the current (terminal) state based on score and available moves (as a heuristic).
        """
        # Current scores
        my_score = state.scores[my_agent_id - 1]
        opp_score = state.scores[2 - my_agent_id]

        # Available moves
        my_area = self.get_playable_squares(state, my_agent_id) or []
        opp_area = self.get_playable_squares(state, 3 - my_agent_id) or []

        # Actual points are more important than territory
        # This is something that can/should be tweaked
        return (my_score - opp_score) * 12 + (len(my_area) - len(opp_area))

    def get_playable_squares(self, game_state: GameState, player: int) -> Optional[List[Square]]:
        """
        Return the list of squares where the player can play.
        It is a copy of the player_squares(self) function in the GameState class.
        """
        allowed_squares = game_state.allowed_squares1 if player == 1 else game_state.allowed_squares2
        occupied_squares = game_state.occupied_squares1 if player == 1 else game_state.occupied_squares2
        N = game_state.board.N

        if allowed_squares is None:
            return None

        def is_empty(square: Square) -> bool:
            return game_state.board.get(square) == SudokuBoard.empty

        # Find valid neighbours of a given square
        def neighbors(square: Square) -> Iterator[Square]:
            row, col = square

            # Neighbouring squares are either -1, 0, or 1 away both vertically and horizontally
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:         # if it is the same square as the one given
                        continue
                    r, c = row + dr, col + dc       # (r,c) coordinates of neighbouring square
                    if 0 <= r < N and 0 <= c < N:
                        yield r, c

        # Add the empty allowed squares
        result = [s for s in allowed_squares if is_empty(s)]

        # Add the empty neighbors to result
        for s1 in occupied_squares:
            for s2 in neighbors(s1):
                if is_empty(s2):
                    result.append(s2)

        # Remove duplicates
        return sorted(list(set(result)))