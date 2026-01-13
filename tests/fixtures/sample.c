#include <stdio.h>
#include <stdlib.h>

#define MAX_SIZE 100
#define MIN(a, b) ((a) < (b) ? (a) : (b))

// Structure for a point
struct Point {
    int x;
    int y;
};

typedef struct Point Point_t;

enum Status {
    SUCCESS,
    FAILURE,
    PENDING
};

/**
 * Calculates the sum of two integers
 * Returns the sum
 */
int add(int a, int b) {
    return a + b;
}

// Multiplies two numbers
int multiply(int x, int y) {
    return x * y;
}

void print_hello(void) {
    printf("Hello, World!\n");
}

int main(int argc, char *argv[]) {
    int result = add(5, 3);
    printf("Result: %d\n", result);
    return 0;
}
