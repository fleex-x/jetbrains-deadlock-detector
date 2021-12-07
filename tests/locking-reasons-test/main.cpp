#include <iostream>
#include <thread>
#include <mutex>
#include <shared_mutex>

void no_opearation() {
	int x = 0;
}

int main() {
	std::shared_mutex m2; 
	std::mutex        m3; 
	std::shared_mutex m4;

	std::shared_lock<std::shared_mutex> l0(m4);
	no_opearation(); //main started

	std::thread t1([&]() {
		no_opearation(); //thread started working
		std::shared_lock<std::shared_mutex> l2(m2);
	});
	
	std::thread t2([&]() {
		std::unique_lock<std::shared_mutex> l1(m2); 
		
		no_opearation(); //thread started working
		
		std::unique_lock<std::mutex> l2(m3);
	});

	std::thread t3([&]() {
		std::unique_lock<std::mutex> l1(m3);
		
		no_opearation(); //thread started working
		
		std::unique_lock<std::shared_mutex>        l2(m4); 
	});
	
	t1.join();
	t2.join();
	return 0;
}