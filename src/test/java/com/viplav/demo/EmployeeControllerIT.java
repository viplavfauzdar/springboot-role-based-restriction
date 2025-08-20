package com.viplav.demo;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.viplav.demo.entity.Employee;
import com.viplav.demo.repository.EmployeeRepository;

import org.springframework.security.test.context.support.WithMockUser;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class EmployeeControllerIT {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private EmployeeRepository repository;

    @BeforeEach
    void setup() {
        repository.deleteAll();
        repository.save(new Employee(null, "John Doe", "Developer"));
    }

    @Test
    @WithMockUser(roles = "USER")
    void shouldReturnEmployeeList() throws Exception {
        mockMvc.perform(get("/api/employees"))
               .andExpect(status().isOk())
               .andExpect(jsonPath("$", hasSize(1)))
               .andExpect(jsonPath("$[0].name", is("John Doe")));
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    void shouldCreateNewEmployee() throws Exception {
        String json = "{\"name\":\"Jane Doe\",\"role\":\"Tester\"}";
        mockMvc.perform(post("/api/employees").with(csrf())
               .contentType(MediaType.APPLICATION_JSON)
               .content(json))
               .andExpect(status().isOk())
               .andExpect(jsonPath("$.name", is("Jane Doe")));
    }
}
