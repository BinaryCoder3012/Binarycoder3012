import os
import re
import sys

def check_winner(board):
    win_patterns = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # Cols
        [0, 4, 8], [2, 4, 6]             # Diagonals
    ]
    for p in win_patterns:
        if board[p[0]] != '-' and board[p[0]] == board[p[1]] == board[p[2]]:
            return board[p[0]]
    if '-' not in board:
        return 'draw'
    return None

def generate_table(board):
    url_blank = "https://placehold.co/50x50/1e1e2e/1e1e2e.png"
    url_x = "https://placehold.co/50x50/1e1e2e/ff5555.png?text=X"
    url_o = "https://placehold.co/50x50/1e1e2e/5555ff.png?text=O"
    
    table = "<table>\n"
    for row in range(3):
        table += "  <tr>\n"
        for col in range(3):
            idx = row * 3 + col
            val = board[idx]
            
            img = url_blank
            if val == 'x': img = url_x
            elif val == 'o': img = url_o
            
            if val == '-':
                # Link to create an issue
                issue_url = f"https://github.com/BinaryCoder3012/BinaryCoder3012/issues/new?title=ttt%7C{idx}&body=Just+submit+this+issue+to+play+your+move!"
                cell = f'<a href="{issue_url}"><img src="{img}" width="50" height="50"></a>'
            else:
                cell = f'<img src="{img}" width="50" height="50">'
                
            table += f"    <td>{cell}</td>\n"
        table += "  </tr>\n"
    table += "</table>\n"
    return table

def main():
    issue_title = os.environ.get("ISSUE_TITLE", "")
    if not issue_title.startswith("ttt|"):
        print("Not a tic-tac-toe move. Exiting.")
        sys.exit(0)
        
    try:
        move_idx = int(issue_title.split("|")[1])
    except (IndexError, ValueError):
        print("Invalid move format.")
        sys.exit(0)
        
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found.")
        sys.exit(1)
        
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    state_match = re.search(r'<!-- tictactoe_state: (.{9}) -->', content)
    if not state_match:
        print("State not found in README.")
        sys.exit(1)
        
    state = list(state_match.group(1))
    
    # Verify move is valid
    if move_idx < 0 or move_idx > 8 or state[move_idx] != '-':
        print("Invalid move.")
        sys.exit(0)
        
    # Determine whose turn it is
    x_count = state.count('x')
    o_count = state.count('o')
    player = 'x' if x_count == o_count else 'o'
    
    # Make move
    state[move_idx] = player
    
    # Check for win or draw
    winner = check_winner(state)
    status_msg = f"<b>{player.upper()} just played! It is now {'O' if player == 'x' else 'X'}'s turn.</b>"
    
    if winner:
        if winner == 'draw':
            status_msg = "<b>It's a draw! Board has been reset.</b>"
        else:
            status_msg = f"<b>{winner.upper()} won the last game! Board has been reset.</b>"
        state = list("---------")
        
    new_state_str = "".join(state)
    new_table = generate_table(state)
    
    # Update README
    content = re.sub(r'<!-- tictactoe_state: (.{9}) -->', f'<!-- tictactoe_state: {new_state_str} -->', content)
    
    board_regex = r'<!-- tictactoe_board_start -->.*?<!-- tictactoe_board_end -->'
    new_board_block = f"<!-- tictactoe_board_start -->\n{status_msg}\n<br/>\n{new_table}<!-- tictactoe_board_end -->"
    content = re.sub(board_regex, new_board_block, content, flags=re.DOTALL)
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("README updated successfully.")

if __name__ == "__main__":
    main()

