
package com.viplav.demo;

import io.micrometer.core.instrument.MeterRegistry;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class MetricInit {
    private final MeterRegistry registry;

    public MetricInit(MeterRegistry registry) {
        this.registry = registry;
    }

    @PostConstruct
    public void init() {
        registry.counter("custom.startup.count").increment();
    }
}
