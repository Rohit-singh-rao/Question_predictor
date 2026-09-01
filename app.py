from main import run_parser, update_metadata
from predict import run_predictor
from search import search_questions
from analytics import run_analytics

def main_menu():
    while True:
        print("\n" + "="*33)
        print("   QUESTION PREDICTOR ENGINE     ")
        print("="*33)
        print("1. Parse Raw Text / PDF (main.py)")
        print("2. Search Questions (search.py)")
        print("3. Generate Prediction Report (predict.py)")
        print("4. Edit Question Metadata (main.py)")
        print("5. View Analytics Dashboard (analytics.py)")
        print("6. Exit")

        choice = input("\nSelect an option (1-6): ").strip()

        if choice == "1":
            run_parser()
        elif choice == "2":
            search_questions()
        elif choice == "3":
            run_predictor()
        elif choice == "4":
            update_metadata()
        elif choice == "5":
            run_analytics()
        elif choice == "6":
            print("\nExiting Question Predictor. Goodbye!")
            break
        else:
            print("\n[!] Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main_menu()