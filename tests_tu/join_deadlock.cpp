#include <iostream>
#include <thread>
#include <mutex>

int main() {
	std::mutex m1;
	std::unique_lock<std::mutex> l2(m1);

	std::thread t1([&](){
		std::unique_lock<std::mutex> l1(m1);
	});
	
	t1.join();
	return 0;
}
