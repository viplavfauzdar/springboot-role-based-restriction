package com.viplav.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.viplav.demo.entity.Employee;

public interface EmployeeRepository extends JpaRepository<Employee, Long> {
}
