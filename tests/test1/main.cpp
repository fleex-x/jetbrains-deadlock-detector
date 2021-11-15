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
	const int N = 100;
	std::thread t1([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m1);
			std::unique_lock<std::mutex> l2(m2);
			std::unique_lock<std::mutex> l3(m5);
		}

	});
	std::thread t2([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m2);
			std::unique_lock<std::mutex> l2(m3);
			std::unique_lock<std::mutex> l3(m5);
		}
	});
	std::thread t3([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m3);
			std::unique_lock<std::mutex> l2(m4);
			std::unique_lock<std::mutex> l3(m6);
		}

	});
	std::thread t4([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l2(m4);
			std::unique_lock<std::mutex> l1(m5);
		}
	});
	std::thread t5([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m5);
			std::unique_lock<std::mutex> l2(m6);
		}

	});
	std::thread t6([&]() {
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l2(m6);
		}
	});

	for (int i = 0; i < 10; ++i) {
		//breakpoint
		std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(20));
	}

	t1.join();
	t2.join();
	t3.join();
	t4.join();
	t5.join();
	t6.join();
	return 0;
}
