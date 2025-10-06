#include <iostream>

int main() {
    int a = 3, b = 4;
    std::cout << "Sum: " << (a + b) << std::endl;

    int n = 5;
    int* p = new int[n];
    for (int i = 0; i < n; ++i) p[i] = i;
    for (int i = 0; i < n; ++i) std::cout << p[i] << " ";
    std::cout << std::endl;
    delete[] p;
    return 0;
}
