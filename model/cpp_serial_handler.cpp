#include <pybind11/pybind11.h>
#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>
#include <string>
#include <stdexcept>
#include <iostream>  // Added for debugging prints

namespace py = pybind11;
using namespace boost::asio;

class CppSerialHandler {
public:
    CppSerialHandler(const std::string& port, unsigned int baud_rate, double timeout)
        : io(), serial(io), port_name(port), baud_rate(baud_rate), timeout_seconds(timeout), is_open(false)
    {
        std::cout << "[CppSerialHandler] Initialized for port " << port_name
                  << " with baud rate " << baud_rate << std::endl;
    }

    void open() {
        std::cout << "[CppSerialHandler] Attempting to open serial port: " << port_name << std::endl;
        boost::system::error_code ec;
        serial.open(port_name, ec);
        if (ec) {
            std::cerr << "[CppSerialHandler] Error opening serial port: " << ec.message() << std::endl;
            throw std::runtime_error("Error opening serial port: " + ec.message());
        }
        serial.set_option(serial_port_base::baud_rate(baud_rate), ec);
        if (ec) {
            std::cerr << "[CppSerialHandler] Error setting baud rate: " << ec.message() << std::endl;
            throw std::runtime_error("Error setting baud rate: " + ec.message());
        }
        is_open = true;
        std::cout << "[CppSerialHandler] Serial port opened successfully." << std::endl;
    }

    void close() {
        if (is_open) {
            std::cout << "[CppSerialHandler] Closing serial port: " << port_name << std::endl;
            boost::system::error_code ec;
            serial.close(ec);
            if (ec) {
                std::cerr << "[CppSerialHandler] Error closing serial port: " << ec.message() << std::endl;
            } else {
                std::cout << "[CppSerialHandler] Serial port closed successfully." << std::endl;
            }
            is_open = false;
        }
    }

    void write_bytes(py::bytes data) {
        if (!is_open) {
            std::cerr << "[CppSerialHandler] write_bytes called but serial port not open." << std::endl;
            throw std::runtime_error("Serial port not open");
        }
        std::string data_str = data; // convert py::bytes to std::string
        std::cout << "[CppSerialHandler] Writing bytes: " << data_str << std::endl;
        boost::asio::write(serial, boost::asio::buffer(data_str));
        std::cout << "[CppSerialHandler] Write complete." << std::endl;
    }

    py::bytes read_line() {
        if (!is_open) {
            std::cerr << "[CppSerialHandler] read_line called but serial port not open." << std::endl;
            throw std::runtime_error("Serial port not open");
        }
        char c;
        std::string result;
        boost::system::error_code ec;
        std::cout << "[CppSerialHandler] Starting to read line..." << std::endl;
        // Read until a newline, carriage return, or ETX (0x03) is encountered.
        while (true) {
            size_t n = boost::asio::read(serial, boost::asio::buffer(&c, 1), ec);
            if (ec) {
                std::cerr << "[CppSerialHandler] Error reading from serial port: " << ec.message() << std::endl;
                throw std::runtime_error("Error reading from serial port: " + ec.message());
            }
            if (n > 0) {
                std::cout << "[CppSerialHandler] Read char: " << c << std::endl;
                // Break on newline, carriage return, or ETX
                if (c == '\n' || c == '\r' || c == '\x03') {
                    std::cout << "[CppSerialHandler] End of response detected." << std::endl;
                    break;
                }
                result.push_back(c);
            }
        }
        std::cout << "[CppSerialHandler] Completed read line: " << result << std::endl;
        return py::bytes(result);
    }

private:
    boost::asio::io_context io;
    boost::asio::serial_port serial;
    std::string port_name;
    unsigned int baud_rate;
    double timeout_seconds;
    bool is_open;
};

PYBIND11_MODULE(cpp_serial_handler, m) {
    py::class_<CppSerialHandler>(m, "CppSerialHandler")
        .def(py::init<const std::string&, unsigned int, double>())
        .def("open", &CppSerialHandler::open)
        .def("close", &CppSerialHandler::close)
        .def("write_bytes", &CppSerialHandler::write_bytes)
        .def("read_line", &CppSerialHandler::read_line);
}
