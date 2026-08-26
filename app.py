import sys
import subprocess

def show_menu():
    print("\n=================================")
    print("   QUESTION PREDICTOR ENGINE     ")
    print("=================================")
    print("1. Parse Raw Text (main.py)")
    print("2. Search Questions (search.py)")
    print("3. Generate Prediction Report (predict.py)")
    print("4. Exit")

def main():
    while True:
        show_menu()
        choice = input("\nSelect an option (1-4): ").strip()

        if choice == "1":
            print("\n[Running main.py...]")
            subprocess.run([sys.executable, "main.py"])
        elif choice == "2":
            print("\n[Running search.py...]")
            subprocess.run([sys.executable, "search.py"])
        elif choice == "3":
            print("\n[Running predict.py...]")
            subprocess.run([sys.executable, "predict.py"])
        elif choice == "4":
            print("\nExiting Question Predictor. Goodbye!")
            break
        else:
            print("\nInvalid selection. Please choose 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()