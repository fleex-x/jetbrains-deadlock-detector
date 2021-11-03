#include <iostream>
#include <thread>
#include <mutex>

int main() {
	std::mutex m1;
	std::mutex m2;
	std::thread t1([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l1(m1);
			std::unique_lock<std::mutex> l2(m2);
		}

	});
	std::thread t2([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l2(m2);
			std::unique_lock<std::mutex> l1(m1);
		}
	});

	t1.join();
	t2.join();
	return 0;
}
