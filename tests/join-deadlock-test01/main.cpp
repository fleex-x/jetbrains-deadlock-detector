#include <iostream>
#include <thread>
#include <mutex>

void no_opearation() {
	int x = 0;
}

int main() {
	std::mutex m0;
	std::mutex m1;
	std::mutex m2;
	std::mutex m3;
	std::mutex m4;
	std::unique_lock<std::mutex> l0(m0);
	no_opearation(); //main started

	std::thread t1([&](){ 
		std::unique_lock<std::mutex> l1(m1);
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m2);
	});

	std::thread t2([&](){
		std::unique_lock<std::mutex> l1(m2);
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m3);
	});

	std::thread t3([&](){
		std::unique_lock<std::mutex> l1(m3);
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l2(m4);
	});

	std::thread t4([&](){
		std::unique_lock<std::mutex> l2(m4);
		no_opearation(); //thread started working
		t1.join();
	});


	t2.join();
	t1.join();
	t3.join();
	t4.join();
	return 0;
}
