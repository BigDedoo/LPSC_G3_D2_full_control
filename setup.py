from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
   Pybind11Extension(
       "cpp_serial_handler",
       ["model/cpp_serial_handler.cpp"],
       include_dirs=[
           "C:/Users/gemond/boost_1_87_0",  # Boost headers
       ],
       library_dirs=["C:/Users/gemond/boost_1_87_0/libs"],













































































































































       language="c++",
       extra_compile_args=["-std=c++17"],  # GCC flag for C++17
   ),
]

setup(
   name="cpp_serial_handler",
   version="0.0.1",
   author="Your Name",
   author_email="your.email@example.com",
   description="A C++ extension module for serial handling",
   ext_modules=ext_modules,
   cmdclass={"build_ext": build_ext},
   zip_safe=False,
)
