#include <iostream>
#include <stdlib.h>

#define MAX 5  // Define maximum size of the deque

int deque[MAX];
int front = -1;
int rear = -1;

// Function to check if the deque is full
int isFull() {
    return ((front == 0 && rear == MAX - 1) || (front == rear + 1));
}

// Function to check if the deque is empty
int isEmpty() {
    return (front == -1);
}

// Function to insert an element at the front of the deque
void insertFront(int key) {
    if (isFull()) {
        std::cout << "Overflow: Unable to insert element at the front. Deque is full." << std::endl;
        return;
    }

    if (front == -1) {  // If deque is initially empty
        front = 0;
        rear = 0;
    } else if (front == 0) {
        front = MAX - 1;  // wrap around
    } else {
        front = front - 1;
    }

    deque[front] = key;
    std::cout << "Inserted " << (key) << " at the front." << std::endl;
}

// Function to insert an element at the rear of the deque
void insertRear(int key) {
    if (isFull()) {
        std::cout << "Overflow: Unable to insert element at the rear. Deque is full." << std::endl;
        return;
    }

    if (rear == -1) {  // If deque is initially empty
        front = 0;
        rear = 0;
    } else if (rear == MAX - 1) {
        rear = 0;  // wrap around
    } else {
        rear = rear + 1;
    }

    deque[rear] = key;
    std::cout << "Inserted " << (key) << " at the rear." << std::endl;
}

// Function to delete an element from the front of the deque
void deleteFront() {
    if (isEmpty()) {
        std::cout << "Underflow: Unable to delete element from the front. Deque is empty." << std::endl;
        return;
    }

    int removed = deque[front];

    if (front == rear) {  // Deque has only one element
        front = -1;
        rear = -1;
    } else if (front == MAX - 1) {
        front = 0;  // wrap around
    } else {
        front = front + 1;
    }

    std::cout << "Deleted " << (removed) << " from the front." << std::endl;
}

// Function to delete an element from the rear of the deque
void deleteRear() {
    if (isEmpty()) {
        std::cout << "Underflow: Unable to delete element from the rear. Deque is empty." << std::endl;
        return;
    }

    int removed = deque[rear];

    if (front == rear) {  // Deque has only one element
        front = -1;
        rear = -1;
    } else if (rear == 0) {
        rear = MAX - 1;  // wrap around
    } else {
        rear = rear - 1;
    }

    std::cout << "Deleted " << (removed) << " from the rear." << std::endl;
}

// Function to display the deque
void displayDeque() {
    if (isEmpty()) {
        std::cout << "Deque is empty." << std::endl;
        return;
    }

    std::cout << "Deque elements are: ";
    int i = front;
    while (1) {
        std::cout << (deque[i]) << " ";
        if (i == rear)
            break;
        i = (i + 1) % MAX;
    }
    std::cout << std::endl;
}

// Main function to test the operations
int main() {
    insertRear(5);
    displayDeque();

    insertFront(15);
    displayDeque();
    
    insertRear(25);
    displayDeque();

    deleteFront();
    displayDeque();

    deleteRear();
    displayDeque();


    return 0;
}