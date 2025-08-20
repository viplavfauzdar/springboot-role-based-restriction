package com.viplav.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.viplav.demo.entity.AppUser;

import java.util.Optional;

public interface AppUserRepository extends JpaRepository<AppUser, Long> {
    Optional<AppUser> findByUsername(String username);
}
