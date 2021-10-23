#include <iostream>
#include <thread>
#include <mutex>

struct Foo {
	int x;
};

class Rectangle {
private:
   int height;
   int width;
   Foo k{5};
public:
   Rectangle() : height(3), width(5) {}
   Rectangle(int H) : height(H), width(H*2-1) {}
   Rectangle(int H, int W) : height(H), width(W) {}
   int GetHeight() { return height; }
   int GetWidth() { return width; }
};

int main() {
	std::mutex m1;
	std::mutex m2;
	std::thread t1([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock l1(m1);
			std::unique_lock l2(m2);
		}

	});
	std::thread t2([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock l2(m2);
			std::unique_lock l1(m1);
		}
	});

	t1.join();
	t2.join();
	return 0;
}
