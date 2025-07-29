def fibonacci_recursive(n):
     if n <= 0:
         return 0
     elif n == 1:
         return 1
     else:
         return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)
 
import time
start_time = time.time()
result_recursive = fibonacci_recursive(20)
duration_recursive = time.time() - start_time
result_recursive, duration_recursive
print(f"Recursive Fibonacci result: {result_recursive}, Duration: {duration_recursive} seconds")







