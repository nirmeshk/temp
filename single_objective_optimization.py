from __future__ import division
from PyGMO import problem
from PyGMO import algorithm
from PyGMO import island
import math

class schaffer_function_n2(problem.base):
    """ Schaffer Function N.2
    Reference: http://en.wikipedia.org/wiki/Test_functions_for_optimization#Test_functions_for_single-objective_optimization_problems """
  
    def __init__(self):
        #First we call the constructor of the base class telling
        #essentially to PyGMO what kind of problem to expect (1 objective, 0 contraints etc.)
        dim = 2 #This is schaffer_function with 2 dimensions
        super(schaffer_function_n2,self).__init__(dim)
        #then we set the problem bounds (in this case equal for all components)
        self.set_bounds(-100,100)
        #we define some additional 'private' data members (not really necessary in
        #this case, but ... hey this is a tutorial)
        self.__dim = dim
    
    #We reimplement the virtual method that defines the objective function.
    def _objfun_impl(self, candidate):
        x = candidate[0]
        y = candidate[1]
        #print("x & y :",x,y)
        f = 0.5 + (math.sin(x**2 - y**2)**2 - 0.5) / ( 1 + 0.001*(x**2 + y**2) )**2
        #print("f", f)
        return (f,)
    
    #Finally we also reimplement a virtual method that adds some output to the __repr__ method
    def human_readable_extra(self):
        text = """Problem dimension: %s
               Implemented function: 
               f = 0.5 + (math.sin(x**2 - y**2)**2 - 0.5) / ( 1 + 0.001*(x**2 + y**2) )**2 """ % str(self.__dim)
        return text

class sphere_function(problem.base):
    """ Sphere Function N dimension
    Reference: http://en.wikipedia.org/wiki/Test_functions_for_optimization#Test_functions_for_single-objective_optimization_problems """
  
    def __init__(self, dim = 10):
        #First we call the constructor of the base class telling
        #essentially to PyGMO what kind of problem to expect (1 objective, 0 contraints etc.)
        super(sphere_function,self).__init__(dim)
        #then we set the problem bounds (in this case equal for all components)
        self.set_bounds(-100,100)
        #we define some additional 'private' data members (not really necessary in
        #this case, but ... hey this is a tutorial)
        self.__dim = dim
    
    #We reimplement the virtual method that defines the objective function.
    def _objfun_impl(self, x):
        f = 0
        for i in range(self.__dim):
            f += x[i]**2
        return (f,)
    
    #Finally we also reimplement a virtual method that adds some output to the __repr__ method
    def human_readable_extra(self):
        text = "\n\t Problem dimension: " + str(self.__dim) + "\n\t Implemented function: f = x^2"
        return text



if __name__ == '__main__':

    print("############### Differential Evolution ##########################")
    prob = schaffer_function_n2()
    print(prob)
    algo = algorithm.de(gen = 500)
    isl = island(algo,prob,50)
    print("Before optimisation")
    print(isl.population.champion.f)
    isl.evolve(10)
    print("After optimisation")
    print(isl.population.champion.f)

    print("-"*70)
    print("Sphere Function")
    prob2 = sphere_function(dim=100)
    print(prob2)
    isl2 = island(algo,prob2,50)
    print("Before optimisation")
    print(isl2.population.champion.f)
    isl2.evolve(10)
    print("After optimisation")
    print(isl2.population.champion.f)

    print("############### Simulated Anealing ##########################")

    algo3 = algorithm.sa_corana()
    isl3 = island(algo3,prob,50)
    print(prob)
    print("Before optimisation")
    print(isl3.population.champion.f)
    isl3.evolve(10)
    print("After optimisation")
    print(isl3.population.champion.f)
    
    print("-"*70)
    print(prob2)
    isl4 = island(algo3,prob2,50)
    print("Before optimisation")
    print(isl4.population.champion.f)
    isl4.evolve(10)
    print("After optimisation")
    print(isl4.population.champion.f)