package com.viplav.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.viplav.demo.entity.AppRole;

public interface AppRoleRepository extends JpaRepository<AppRole, Long> {
    AppRole findByName(String name);
}
