import sys
from main import run_parser
from search import search_questions
from predict import run_predictor

def display_menu():
    print("\n" + "="*35)
    print("   QUESTION PREDICTOR CLI ENGINE   ")
    print("="*35)
    print("1. Parse Raw Text / PDF Files")
    print("2. Search Questions by Keyword/Topic")
    print("3. Generate Topic Frequency Report")
    print("4. Exit")
    print("="*35)

def main():
    while True:
        display_menu()
        choice = input("\nSelect an option (1-4): ").strip()

        if choice == "1":
            run_parser()
        elif choice == "2":
            search_questions()
        elif choice == "3":
            run_predictor()
        elif choice == "4":
            print("\nExiting Question Predictor. Goodbye!")
            sys.exit(0)
        else:
            print("\n[!] Invalid selection. Please enter a number between 1 and 4.")

if __name__ == "__main__":
    main()