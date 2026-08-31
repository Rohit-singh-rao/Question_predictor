from main import run_parser, update_metadata
from search import run_search
from predict import run_predictor
from analytics import run_analytics  # 1. Imported our new module

def show_menu():
    print("\n=================================")
    print("   QUESTION PREDICTOR ENGINE     ")
    print("=================================")
    print("1. Parse Raw Text (main.py)")
    print("2. Search Questions (search.py)")
    print("3. Generate Prediction Report (predict.py)")
    print("4. Edit Question Metadata (main.py)")
    print("5. View Analytics Dashboard (analytics.py)")  # 2. Added new menu item
    print("6. Exit")

def main():
    while True:
        show_menu()
        choice = input("\nSelect an option (1-6): ").strip()

        if choice == "1":
            run_parser()
        elif choice == "2":
            run_search()
        elif choice == "3":
            run_predictor()
        elif choice == "4":
            update_metadata()
        elif choice == "5":
            run_analytics()  # Executes our analytics module
        elif choice == "6":
            print("\nExiting Question Predictor. Goodbye!")
            break
        else:
            print("\nInvalid selection. Please choose 1-6.")

if __name__ == "__main__":
    main()