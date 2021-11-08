#include <iostream>
#include <thread>
#include <mutex>

int main() {
	std::mutex m1;
	std::mutex m2;
	std::mutex m3;
	std::mutex m4;
	std::mutex m5;
	std::mutex m6;
	std::mutex m7;
	std::mutex m8;
	std::thread t1([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l1(m1);
			std::unique_lock<std::mutex> l2(m2);
		}

	});
	std::thread t2([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l2(m2);
			std::unique_lock<std::mutex> l1(m3);
		}
	});
	std::thread t3([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l1(m3);
			std::unique_lock<std::mutex> l2(m4);
		}

	});
	std::thread t4([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l2(m4);
			std::unique_lock<std::mutex> l1(m5);
		}
	});
	std::thread t5([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l1(m5);
			std::unique_lock<std::mutex> l2(m6);
		}

	});
	std::thread t6([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l2(m6);
			std::unique_lock<std::mutex> l1(m7);
		}
	});
	std::thread t7([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l1(m7);
			std::unique_lock<std::mutex> l2(m8);
		}

	});
	std::thread t8([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::mutex> l2(m8);
		}
	});

	t1.join();
	t2.join();
	t3.join();
	t4.join();
	t5.join();
	t6.join();
	t7.join();
	t8.join();
	return 0;
}
