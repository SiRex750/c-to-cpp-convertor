#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

// C translation of the C++ templated Deque<T>, specialized to int

typedef struct Node {
    int data;
    struct Node* prev;
    struct Node* next;
} Node;

typedef struct Deque {
    Node* front;
    Node* rear;
    int size;
} Deque;

// Initialize an empty deque
void deque_init(Deque* dq) {
    dq->front = NULL;
    dq->rear = NULL;
    dq->size = 0;
}

// Check if empty
bool deque_is_empty(Deque* dq) {
    return dq->size == 0;
}

// Push to front
void deque_push_front(Deque* dq, int value) {
    Node* new_node = (Node*)malloc(sizeof(Node));
    if (!new_node) {
        fprintf(stderr, "Allocation failed\n");
        exit(1);
    }
    new_node->data = value;
    new_node->prev = NULL;
    new_node->next = dq->front;
    if (deque_is_empty(dq)) {
        dq->front = dq->rear = new_node;
    } else {
        dq->front->prev = new_node;
        dq->front = new_node;
    }
    dq->size++;
}

// Push to back
void deque_push_back(Deque* dq, int value) {
    Node* new_node = (Node*)malloc(sizeof(Node));
    if (!new_node) {
        fprintf(stderr, "Allocation failed\n");
        exit(1);
    }
    new_node->data = value;
    new_node->next = NULL;
    new_node->prev = dq->rear;
    if (deque_is_empty(dq)) {
        dq->front = dq->rear = new_node;
    } else {
        dq->rear->next = new_node;
        dq->rear = new_node;
    }
    dq->size++;
}

// Pop from front; exits with error if empty to match exception semantics
void deque_pop_front(Deque* dq) {
    if (deque_is_empty(dq)) {
        fprintf(stderr, "Deque is empty\n");
        exit(1);
    }
    Node* temp = dq->front;
    dq->front = dq->front->next;
    if (dq->front == NULL) {
        dq->rear = NULL;
    } else {
        dq->front->prev = NULL;
    }
    free(temp);
    dq->size--;
}

// Pop from back; exits with error if empty
void deque_pop_back(Deque* dq) {
    if (deque_is_empty(dq)) {
        fprintf(stderr, "Deque is empty\n");
        exit(1);
    }
    Node* temp = dq->rear;
    dq->rear = dq->rear->prev;
    if (dq->rear == NULL) {
        dq->front = NULL;
    } else {
        dq->rear->next = NULL;
    }
    free(temp);
    dq->size--;
}

// Get front value; exits if empty
int deque_get_front(Deque* dq) {
    if (deque_is_empty(dq)) {
        fprintf(stderr, "Deque is empty\n");
        exit(1);
    }
    return dq->front->data;
}

// Get rear value; exits if empty
int deque_get_rear(Deque* dq) {
    if (deque_is_empty(dq)) {
        fprintf(stderr, "Deque is empty\n");
        exit(1);
    }
    return dq->rear->data;
}

// Get size
int deque_get_size(Deque* dq) {
    return dq->size;
}

// Display elements
void deque_display(Deque* dq) {
    Node* cur = dq->front;
    while (cur != NULL) {
        printf("%d ", cur->data);
        cur = cur->next;
    }
    printf("\n");
}

// Destroy and free all nodes
void deque_destroy(Deque* dq) {
    while (!deque_is_empty(dq)) {
        deque_pop_front(dq);
    }
}

int main(void) {
    Deque dq;
    deque_init(&dq);

    // Push elements to the front and back
    deque_push_front(&dq, 10);
    deque_push_back(&dq, 20);
    deque_push_front(&dq, 5);
    deque_push_back(&dq, 30);

    // Display the Deque after pushes
    printf("Deque after pushes: ");
    deque_display(&dq);

    // Get and display the front and rear elements
    printf("Front element: %d\n", deque_get_front(&dq));
    printf("Rear element: %d\n", deque_get_rear(&dq));

    // Pop elements from the front and back
    deque_pop_front(&dq);
    deque_pop_back(&dq);

    // Display the Deque after pops
    printf("Deque after pops: ");
    deque_display(&dq);

    // Display the size of the Deque
    printf("Size of deque: %d\n", deque_get_size(&dq));

    deque_destroy(&dq);
    return 0;
}
