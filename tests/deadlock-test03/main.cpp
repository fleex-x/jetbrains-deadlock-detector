#include <iostream>
#include <thread>
#include <mutex>

void no_opearation() {
	int x = 0;
}

int main() {
	std::mutex m1; 
	std::mutex m2;
	std::mutex m3;
	std::mutex m4;
	std::mutex m5;
	std::mutex m6;
	std::mutex m7; 
	no_opearation(); //main started
	std::thread t1([&]() { 
		std::unique_lock<std::mutex> l1(m1); 
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m2);
	});
	std::thread t2([&]() {
		std::unique_lock<std::mutex> l1(m2);
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m3);
	});
	std::thread t3([&]() {          
		std::unique_lock<std::mutex> l1(m3);  
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m4);
	});
	std::thread t4([&]() {          
		std::unique_lock<std::mutex> l1(m4);  
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m5);
	});
	std::thread t5([&]() {          
		std::unique_lock<std::mutex> l1(m5);  
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m6);
	});
	std::thread t6([&]() {         
		std::unique_lock<std::mutex> l1(m6);  
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m7);
	});
	std::thread t7([&]() {          
		std::unique_lock<std::mutex> l1(m7); 
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m5);
	});
	t1.join();
	t2.join();
	t3.join();
	t4.join();
	t5.join();
	t6.join();
	t7.join();
	return 0;
}