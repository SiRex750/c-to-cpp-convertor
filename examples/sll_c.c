#include <stdio.h>
#include <stdlib.h>

struct Node {
    int data;
    struct Node* next;
};

struct Node* push_front(struct Node* head, int value) {
    struct Node* n = (struct Node*)malloc(sizeof(struct Node));
    n->data = value;
    n->next = head;
    return n;
}

void print_list(struct Node* head) {
    struct Node* cur = head;
    while (cur) {
        printf("%d ", cur->data);
        cur = cur->next;
    }
    printf("\n");
}

void free_list(struct Node* head) {
    while (head) {
        struct Node* tmp = head->next;
        free(head);
        head = tmp;
    }
}

int main() {
    struct Node* head = NULL;
    for (int i = 0; i < 5; ++i) {
        head = push_front(head, i);
    }
    print_list(head);
    free_list(head);
    return 0;
}
