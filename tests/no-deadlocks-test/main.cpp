#include <iostream>
#include <thread>
#include <mutex>
#include <condition_variable>

namespace {
class latch {
private:
    std::mutex m;
    int counter;
    std::condition_variable counter_changed;

public:
    explicit latch(int counter_) : counter(counter_) {
    }
    void arrive_and_wait() {
        std::unique_lock l(m);
        counter--;
        counter_changed.notify_all();
        counter_changed.wait(l, [&]() { return counter <= 0; });
    }
};
}  // namespace

void no_operation() {
	int x = 0;
}

int main() {
	std::mutex m1;
	std::mutex m2;
	std::mutex m3;
	std::mutex m4;
	std::mutex m5;
	std::mutex m6;
	const int N = 50;
	latch latch(6);
	std::thread t1([&]() {
		latch.arrive_and_wait();
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m1);
			std::unique_lock<std::mutex> l2(m2);
			std::unique_lock<std::mutex> l3(m5);
		}

	});
	std::thread t2([&]() {
		latch.arrive_and_wait();
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m2);
			std::unique_lock<std::mutex> l2(m3);
			std::unique_lock<std::mutex> l3(m5);
		}
	});
	std::thread t3([&]() {
		latch.arrive_and_wait();
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m3);
			std::unique_lock<std::mutex> l2(m4);
			std::unique_lock<std::mutex> l3(m5);
		}

	});
	std::thread t4([&]() {
		latch.arrive_and_wait();
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l2(m4);
			std::unique_lock<std::mutex> l1(m5);
		}
	});
	std::thread t5([&]() {
		latch.arrive_and_wait();
		for (int i = 0; i < N; ++i) {
			std::unique_lock<std::mutex> l1(m5); 
			no_operation();//breakpoint
		}

	});

	latch.arrive_and_wait();
	for (int i = 0; i < 30; ++i) {
		//breakpoint
		std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(20));
	}

	t1.join();
	t2.join();
	t3.join();
	t4.join();
	t5.join();
	return 0;
}
