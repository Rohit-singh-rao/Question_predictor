import sys
from main import run_parser, update_metadata
from search import search_questions
from predict import run_predictor
from analytics import run_analytics
from export import export_prediction_report

def display_menu():
    print("\n" + "="*35)
    print("   QUESTION PREDICTOR CLI ENGINE   ")
    print("="*35)
    print("1. Parse Raw Text / PDF File")
    print("2. Search Questions by Keyword/Topic")
    print("3. Generate Prediction Report")
    print("4. Edit Question Metadata")
    print("5. View Analytics Dashboard")
    print("6. Export Prediction Report (.txt / .md)")
    print("7. Exit")
    print("="*35)

def main():
    while True:
        display_menu()
        choice = input("\nSelect an option (1-7): ").strip()

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
            export_prediction_report()
        elif choice == "7":
            print("\nExiting Question Predictor. Goodbye!")
            sys.exit(0)
        else:
            print("\n[!] Invalid selection. Please enter a number between 1 and 7.")

if __name__ == "__main__":
    main()