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
	std::mutex        m3;
	std::unique_lock<std::mutex>         l0(m3);
	no_opearation(); //main started
	std::thread t1([&]() {
		std::unique_lock<std::shared_mutex> l1(m1); 
		no_opearation(); //thread started working
		std::shared_lock<std::shared_mutex> l2(m2);
	});
	std::thread t2([&]() {
		std::unique_lock<std::shared_mutex> l1(m2);
		no_opearation(); //thread started working
		std::unique_lock<std::mutex>         l2(m3); 
	});
	
	t1.join();
	t2.join();
	return 0;
}