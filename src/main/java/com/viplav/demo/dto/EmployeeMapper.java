package com.viplav.demo.dto;

import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import com.viplav.demo.entity.Employee;

@Mapper
public interface EmployeeMapper {
    EmployeeMapper INSTANCE = Mappers.getMapper(EmployeeMapper.class);

    EmployeeDTO toDTO(Employee employee);
    Employee toEntity(EmployeeDTO dto);
}
