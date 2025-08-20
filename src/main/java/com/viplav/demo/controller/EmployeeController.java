package com.viplav.demo.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import com.viplav.demo.dto.EmployeeDTO;
import com.viplav.demo.dto.EmployeeMapper;
import com.viplav.demo.entity.Employee;
import com.viplav.demo.service.EmployeeService;

import java.util.List;
import java.util.stream.Collectors;

@CrossOrigin(origins = "http://localhost:3000")
@RestController
@RequestMapping("/api/employees")
public class EmployeeController {
    @Autowired
    private EmployeeService service;

    private final EmployeeMapper mapper = EmployeeMapper.INSTANCE;

    @GetMapping
    public List<EmployeeDTO> getAll() {
        return service.getAllEmployees()
                .stream()
                .map(mapper::toDTO)
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public EmployeeDTO getById(@PathVariable Long id) {
        return mapper.toDTO(service.getEmployeeById(id));
    }

    @PostMapping
    public EmployeeDTO create(@RequestBody EmployeeDTO empDto) {
        Employee employee = mapper.toEntity(empDto);
        return mapper.toDTO(service.createEmployee(employee));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void delete(@PathVariable Long id) {
        service.deleteEmployee(id);
    }

}
