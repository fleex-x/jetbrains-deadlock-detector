#include <iostream>
#include <thread>
#include <mutex>

void no_opearation() {
	int x = 0;
}

int main() {
	std::mutex m0;
	std::unique_lock<std::mutex> l0(m0);
	no_opearation(); //main started

	std::thread t1([&](){
		no_opearation(); //thread started working
		std::unique_lock<std::mutex> l1(m0);
	});
	
	t1.join();
	return 0;
}
