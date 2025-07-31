# def fibonacci_recursive(n):
#      if n <= 0:
#          return 0
#      elif n == 1:
#          return 1
#      else:
#          return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)
 
# import time
# start_time = time.time()
# result_recursive = fibonacci_recursive(20)
# duration_recursive = time.time() - start_time
# result_recursive, duration_recursive
# print(f"Recursive Fibonacci result: {result_recursive}, Duration: {duration_recursive} seconds")

# HTTP URL
http_file_url = 'https://raw.githubusercontent.com/orangetw/Tiny-URL-Fuzzer/master/samples.txt'
ADVANCED_TEST_PROMPTS = [
"Analyze these two datasets representing daily temperatures [72, 75, 73, 70, 76] and [65, 63, 68, 70, 71]. Calculate the average, min, max for each dataset and determine if there's a statistically significant difference between them.",
"Calculate the nth Fibonacci number using both recursive and dynamic programming approaches. Compare their performance for n=20 and explain the difference.",

]

print("--------------------------------")
print(f"Prompt 0: \n{ADVANCED_TEST_PROMPTS[0]}")
print("--------------------------------")
print(f"Prompt 1: \n{ADVANCED_TEST_PROMPTS[1]}")

print()

start_prompt = f"Here is the file link: {http_file_url}. Please analyze the file details, metadata and show me the top 10 lines."
additional_prompt = f"After that, also solve this, {ADVANCED_TEST_PROMPTS[1]}, in a different workspace."
final_prompt = f"Critical: Must run both tasks in different workspaces."
full_prompt = f"{start_prompt}{additional_prompt}{final_prompt}"

print("--------------------------------")
print(f"Full Prompt: \n{full_prompt}")







