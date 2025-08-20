package com.viplav.demo;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import com.viplav.demo.entity.Employee;
import com.viplav.demo.repository.EmployeeRepository;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class EmployeeRepositoryTest {

    @Autowired
    private EmployeeRepository repository;

    @Test
    void testCreateEmployee() {
        Employee emp = new Employee(null, "Test User", "Tester");
        Employee saved = repository.save(emp);
        assertThat(saved.getId()).isNotNull();
    }
    
}
