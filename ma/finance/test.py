import time
from tqdm import tqdm

def tester():
    a = [1, 2]
    b = [3, 4]

    iterations = len(a) * len(b)
    print(iterations)

    progress_bar = iter(tqdm(range(iterations-1)))
    
    for i in a:
        for j in b:
            next(progress_bar)


if __name__ == "__main__":
    tester()