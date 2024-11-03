from jupyterchat import *
import os

# Configure API key
os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

# Advanced chat features
%%user 0
Can you help me optimize this code?

def slow_function(n):
    return [i for i in range(n) if i % 2 == 0]

# Using code execution
%%assistant 1
Let's analyze and improve your code:

def optimized_function(n):
    return list(range(0, n, 2))

# Compare performance
import timeit
print(timeit.timeit('slow_function(1000)', globals=globals(), number=1000))
print(timeit.timeit('optimized_function(1000)', globals=globals(), number=1000))
