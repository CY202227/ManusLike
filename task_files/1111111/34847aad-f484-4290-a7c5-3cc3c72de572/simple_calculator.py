def add(x, y):
    return x + y


def subtract(x, y):
    return x - y


def multiply(x, y):
    return x * y


def divide(x, y):
    if y == 0:
        raise ValueError("Cannot divide by zero.")
    return x / y


def main():
    operation = input("Enter operation (add, subtract, multiply, divide): ")
    num1 = float(input("Enter first number: "))
    num2 = float(input("Enter second number: "))

    if operation == 'add':
        print(add(num1, num2))
    elif operation == 'subtract':
        print(subtract(num1, num2))
    elif operation == 'multiply':
        print(multiply(num1, num2))
    elif operation == 'divide':
        try:
            print(divide(num1, num2))
        except ValueError as e:
            print(e)
    else:
        print("Invalid operation")


if __name__ == "__main__":
    main()