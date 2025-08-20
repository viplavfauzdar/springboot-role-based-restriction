package com.viplav.demo.security;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;

@Component
public class JwtUtil {
    private final String SECRET_KEY = Keys.secretKeyFor(SignatureAlgorithm.HS256).toString();

    @Autowired
    private UserDetailsServiceImpl userDetailsService;

    public String generateToken(String username) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("roles", userDetailsService.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(Collectors.toList()));

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(username)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 10)) // 10 hrs
                //.signWith(SignatureAlgorithm.HS256, Base64.getEncoder().encodeToString(SECRET_KEY.getBytes()))
                //.signWith(SignatureAlgorithm.HS256, Keys.hmacShaKeyFor(SECRET_KEY.getBytes(StandardCharsets.UTF_8)))
                .signWith(SignatureAlgorithm.HS256, Keys.hmacShaKeyFor(SECRET_KEY.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }

    public String extractUsername(String token) {
        return Jwts.parser().setSigningKey(Keys.hmacShaKeyFor(SECRET_KEY.getBytes(StandardCharsets.UTF_8)))
                .parseClaimsJws(token)
                .getBody().getSubject();
    }

    public String refreshToken(String oldToken) {
        String username = extractUsername(oldToken);
        return generateToken(username);
    }

    public UserDetails getUserDetails(String username) {
        // Return user details, possibly from a UserDetailsService
        return userDetailsService.loadUserByUsername(username);
    }

    public boolean validateToken(String token, UserDetails userDetails) {
        final String username = extractUsername(token);
        return (username.equals(userDetails.getUsername()) && !isTokenExpired(token));
    }

    private boolean isTokenExpired(String token) {
        Date expiration = Jwts.parser().setSigningKey(Keys.hmacShaKeyFor(SECRET_KEY.getBytes(StandardCharsets.UTF_8)))
                .parseClaimsJws(token)
                .getBody()
                .getExpiration();
        return expiration.before(new Date());
    }
}
