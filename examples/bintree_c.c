#include <stdio.h>
#include <stdlib.h>

// Structure of a Binary Tree Node
struct Node {
    int data;
    struct Node* left;
    struct Node* right;
};

// Function to create a new node
struct Node* newNode(int v) {
    struct Node* node =
      (struct Node*)malloc(sizeof(struct Node));
    node->data = v;
    node->left = NULL;
    node->right = NULL;
    return node;
}

// Function to print preorder traversal
void printPreorder(struct Node* node) {
    if (node == NULL)
        return;

    // Deal with the node
    printf("%d ", node->data);

    // Recur on left subtree
    printPreorder(node->left);

    // Recur on right subtree
    printPreorder(node->right);
}

int main() {
    struct Node* root = newNode(1);
    root->left = newNode(2);
    root->right = newNode(3);
    root->left->left = newNode(4);
    root->left->right = newNode(5);
    root->right->right = newNode(6);
    
    printPreorder(root);
    printf("\n");

    return 0;
}
