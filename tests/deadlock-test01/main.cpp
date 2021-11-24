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

std::mutex m1;
std::mutex m2;

int main() {
	latch latch(2);
	std::thread t1([&]() {
		latch.arrive_and_wait();
		std::unique_lock<std::mutex> l1(m1);
		std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(150));
		//breakpoint
		std::unique_lock<std::mutex> l2(m2);
	});
	std::thread t2([&]() {
		latch.arrive_and_wait();
		std::unique_lock<std::mutex> l2(m2);
		std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(150));
		std::unique_lock<std::mutex> l1(m1);
	});

	t1.join();
	t2.join();
	return 0;
}
