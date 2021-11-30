#include <iostream>
#include <thread>
#include <mutex>
#include <shared_mutex>

void no_opearation() {
	int x = 0;
}

int main() {
	std::shared_mutex m1; 
	std::shared_mutex m2; 
	no_opearation(); //main started
	std::thread t1([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::shared_mutex> l1(m1); 
			no_opearation(); //thread started working
			std::shared_lock<std::shared_mutex> l2(m2);
		}
	});
	std::thread t2([&]() {
		for (int i = 0; i < 10000; ++i) {
			std::unique_lock<std::shared_mutex> l1(m2);
			no_opearation(); //thread started working
			std::unique_lock<std::shared_mutex> l2(m1);
		}
	});
	
	t1.join();
	t2.join();
	return 0;
}

// 0x00007fffffffdc30