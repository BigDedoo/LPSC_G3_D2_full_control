#include <pybind11/pybind11.h>
#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>
#include <string>
#include <stdexcept>

namespace py = pybind11;
using namespace boost::asio;

class CppSerialHandler {
public:
    CppSerialHandler(const std::string& port, unsigned int baud_rate, double timeout)
        : io(), serial(io), port_name(port), baud_rate(baud_rate), timeout_seconds(timeout), is_open(false)
    {}

    void open() {
        boost::system::error_code ec;
        serial.open(port_name, ec);
        if (ec) {
            throw std::runtime_error("Error opening serial port: " + ec.message());
        }
        serial.set_option(serial_port_base::baud_rate(baud_rate), ec);
        if (ec) {
            throw std::runtime_error("Error setting baud rate: " + ec.message());
        }
        is_open = true;
    }

    void close() {
        if (is_open) {
            boost::system::error_code ec;
            serial.close(ec);
            is_open = false;
        }
    }

    void write_bytes(py::bytes data) {
        if (!is_open) {
            throw std::runtime_error("Serial port not open");
        }
        std::string data_str = data; // convert py::bytes to std::string
        boost::asio::write(serial, boost::asio::buffer(data_str));
    }

    py::bytes read_line() {
        if (!is_open) {
            throw std::runtime_error("Serial port not open");
        }
        char c;
        std::string result;
        boost::system::error_code ec;
        // Read until either a newline or carriage return is encountered.
        while (true) {
            size_t n = boost::asio::read(serial, boost::asio::buffer(&c, 1), ec);
            if (ec) {
                throw std::runtime_error("Error reading from serial port: " + ec.message());
            }
            if (n > 0) {
                if (c == '\n' || c == '\r') {
                    break;
                }
                result.push_back(c);
            }
        }
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
