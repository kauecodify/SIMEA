/**
 * SIMEA API Gateway
 * Sistema Inteligente de Macroeconomia e Estabilidade Ambiental
 * 
 * Main API Gateway that orchestrates all SIMEA services:
 * - HFT Engine (High-Frequency Trading)
 * - Quantum Service
 * - Port Service (SIMEA-Port)
 * - Pool Soberano Management
 */

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import axios, { AxiosError, AxiosInstance } from 'axios';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// ============================================================================
// MIDDLEWARE
// ============================================================================

// Security middleware
app.use(helmet());

// CORS configuration
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
    credentials: true
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000, // limit each IP to 1000 requests per windowMs
    message: {
        status: 'error',
        message: 'Too many requests, please try again later.'
    },
    standardHeaders: true,
    legacyHeaders: false
});
app.use(limiter);

// JSON parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging
app.use((req: Request, res: Response, next: NextFunction) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(`${req.method} ${req.originalUrl} ${res.statusCode} - ${duration}ms`);
    });
    next();
});

// ============================================================================
// SERVICE CLIENTS
// ============================================================================

// Service endpoints from environment or defaults
const services = {
    hft: process.env.HFT_SERVICE_URL || 'http://localhost:4000',
    quantum: process.env.QUANTUM_SERVICE_URL || 'http://localhost:5000',
    port: process.env.PORT_SERVICE_URL || 'http://localhost:5001'
};

// Create axios instances for each service
const serviceClients: Record<string, AxiosInstance> = {};
for (const [name, url] of Object.entries(services)) {
    serviceClients[name] = axios.create({
        baseURL: url,
        timeout: 10000,
        headers: {
            'Content-Type': 'application/json',
            'X-Service': `simea-${name}`
        }
    });
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    if (err instanceof AxiosError) {
        return res.status(err.response?.status || 500).json({
            status: 'error',
            message: err.response?.data?.message || err.message,
            service: err.config?.url
        });
    }
    
    console.error('Error:', err);
    res.status(500).json({
        status: 'error',
        message: 'Internal server error'
    });
});

// ============================================================================
// HEALTH CHECK
// ============================================================================

app.get('/api/health', async (req: Request, res: Response) => {
    try {
        // Check all services
        const healthChecks = await Promise.allSettled([
            serviceClients.hft.get('/health'),
            serviceClients.quantum.get('/health'),
            serviceClients.port.get('/health')
        ]);
        
        const servicesStatus = {
            hft: healthChecks[0].status === 'fulfilled' ? 'healthy' : 'unhealthy',
            quantum: healthChecks[1].status === 'fulfilled' ? 'healthy' : 'unhealthy',
            port: healthChecks[2].status === 'fulfilled' ? 'healthy' : 'unhealthy'
        };
        
        res.json({
            status: 'success',
            service: 'SIMEA API Gateway',
            version: '1.0.0',
            timestamp: new Date().toISOString(),
            services: servicesStatus
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to check service health'
        });
    }
});

// ============================================================================
// POOL SOBERANO ENDPOINTS
// ============================================================================

// Get Pool Soberano companies
app.get('/api/pool/companies', async (req: Request, res: Response) => {
    try {
        const { segment, region, audit, limit = 500, offset = 0 } = req.query;
        
        // In production, this would query the database
        // For now, return mock data matching the frontend expectations
        const companies = generateMockPoolCompanies(limit as number);
        
        // Apply filters
        let filtered = companies;
        if (segment) {
            filtered = filtered.filter(c => c.segment.toLowerCase().includes((segment as string).toLowerCase()));
        }
        if (region) {
            filtered = filtered.filter(c => c.region.toLowerCase() === (region as string).toLowerCase());
        }
        if (audit) {
            filtered = filtered.filter(c => c.audit === audit);
        }
        
        // Apply pagination
        const paginated = filtered.slice(Number(offset), Number(offset) + Number(limit));
        
        res.json({
            status: 'success',
            data: paginated,
            total: filtered.length,
            limit: Number(limit),
            offset: Number(offset)
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to retrieve pool companies'
        });
    }
});

// Get a specific company
app.get('/api/pool/companies/:id', async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const companies = generateMockPoolCompanies(500);
        const company = companies.find(c => c.id === id);
        
        if (!company) {
            return res.status(404).json({
                status: 'error',
                message: 'Company not found'
            });
        }
        
        res.json({
            status: 'success',
            data: company
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to retrieve company'
        });
    }
});

// Get Pool Soberano KPIs
app.get('/api/pool/kpis', async (req: Request, res: Response) => {
    try {
        const companies = generateMockPoolCompanies(500);
        
        const totalPooled = companies.reduce((sum, c) => sum + c.currentBalance, 0);
        const avgYield = companies.reduce((sum, c) => sum + c.yieldPct, 0) / companies.length;
        const auditedVolume = companies.filter(c => c.audit === 'B2G-OK').reduce((sum, c) => sum + c.currentBalance, 0);
        const totalVolume = companies.reduce((sum, c) => sum + c.currentBalance, 0);
        const auditedPct = (auditedVolume / totalVolume * 100);
        
        // Bankruptcy simulation
        const falenciaCount = companies.filter(c => c.isFalencia).length;
        const falenciaVol = companies.filter(c => c.isFalencia).reduce((sum, c) => sum + (c.falenciaContribution || 0), 0);
        
        res.json({
            status: 'success',
            data: {
                totalPooled,
                companiesCount: companies.length,
                avgYield,
                auditedVolume,
                auditedPct: parseFloat(auditedPct.toFixed(2)),
                falenciaCount,
                falenciaVol,
                segments: [...new Set(companies.map(c => c.segment))].length,
                regions: [...new Set(companies.map(c => c.region))].length
            }
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to retrieve pool KPIs'
        });
    }
});

// ============================================================================
// WITHDRAWAL ENDPOINTS
// ============================================================================

// Process PIX withdrawal
app.post('/api/pool/withdraw/pix', async (req: Request, res: Response) => {
    try {
        const { companyId, pixKey, amount, userId } = req.body;
        
        // Validate request
        if (!companyId || !pixKey || !amount || !userId) {
            return res.status(400).json({
                status: 'error',
                message: 'Missing required fields: companyId, pixKey, amount, userId'
            });
        }
        
        // Check user permissions (mock implementation)
        const hasPermission = await checkWithdrawPermission(userId);
        if (!hasPermission) {
            return res.status(403).json({
                status: 'error',
                message: 'Acesso negado: permissao insuficiente'
            });
        }
        
        const companies = generateMockPoolCompanies(500);
        const company = companies.find(c => c.id === companyId);
        
        if (!company) {
            return res.status(404).json({
                status: 'error',
                message: 'Company not found'
            });
        }
        
        // Validate amount
        const numericAmount = Number(amount);
        if (numericAmount <= 0) {
            return res.status(400).json({
                status: 'error',
                message: 'Invalid amount'
            });
        }
        
        if (numericAmount > company.currentBalance) {
            return res.status(400).json({
                status: 'error',
                message: 'Saldo insuficiente para este saque'
            });
        }
        
        // Calculate daily yield and 20% limit
        const dailyYield = calculateDailyYield(company);
        const maxWithdraw = dailyYield * 0.2;
        
        if (numericAmount > maxWithdraw) {
            return res.status(400).json({
                status: 'error',
                message: `Limite excedido: apenas 20% do rendimento diario (R$ ${formatCurrency(maxWithdraw)}) pode ser sacado sem auditoria B2G`
            });
        }
        
        // Process withdrawal
        company.currentBalance -= numericAmount;
        company.totalWithdrawn = (company.totalWithdrawn || 0) + numericAmount;
        
        if (!company.withdrawHistory) {
            company.withdrawHistory = [];
        }
        company.withdrawHistory.push({
            t: Date.now(),
            v: numericAmount,
            key: pixKey,
            type: 'PIX'
        });
        
        // Log transaction for B2G audit
        await logB2GAudit({
            type: 'WITHDRAWAL',
            companyId,
            userId,
            amount: numericAmount,
            method: 'PIX',
            pixKey,
            timestamp: new Date().toISOString()
        });
        
        res.json({
            status: 'success',
            message: `Saque PIX de ${formatCurrency(numericAmount)} enviado para ${company.name}`,
            data: {
                companyId,
                newBalance: company.currentBalance,
                withdrawnAmount: numericAmount,
                maxDailyWithdrawal: maxWithdraw
            }
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to process withdrawal'
        });
    }
});

// Process CNPJ withdrawal (requires B2G audit)
app.post('/api/pool/withdraw/cnpj', async (req: Request, res: Response) => {
    try {
        const { companyId, cnpj, amount, userId, auditCode } = req.body;
        
        // Validate request
        if (!companyId || !cnpj || !amount || !userId || !auditCode) {
            return res.status(400).json({
                status: 'error',
                message: 'Missing required fields'
            });
        }
        
        // Verify B2G audit code
        const isAuditValid = await verifyB2GAuditCode(auditCode, companyId, userId);
        if (!isAuditValid) {
            return res.status(403).json({
                status: 'error',
                message: 'Auditoria B2G invalida ou expirada'
            });
        }
        
        const companies = generateMockPoolCompanies(500);
        const company = companies.find(c => c.id === companyId);
        
        if (!company) {
            return res.status(404).json({
                status: 'error',
                message: 'Company not found'
            });
        }
        
        const numericAmount = Number(amount);
        if (numericAmount <= 0) {
            return res.status(400).json({
                status: 'error',
                message: 'Invalid amount'
            });
        }
        
        if (numericAmount > company.currentBalance) {
            return res.status(400).json({
                status: 'error',
                message: 'Saldo insuficiente para este saque'
            });
        }
        
        // Process withdrawal
        company.currentBalance -= numericAmount;
        company.totalWithdrawn = (company.totalWithdrawn || 0) + numericAmount;
        
        if (!company.withdrawHistory) {
            company.withdrawHistory = [];
        }
        company.withdrawHistory.push({
            t: Date.now(),
            v: numericAmount,
            key: cnpj,
            type: 'CNPJ',
            auditCode
        });
        
        // Log transaction
        await logB2GAudit({
            type: 'WITHDRAWAL_CNPJ',
            companyId,
            userId,
            amount: numericAmount,
            method: 'CNPJ',
            cnpj,
            auditCode,
            timestamp: new Date().toISOString()
        });
        
        res.json({
            status: 'success',
            message: `Saque CNPJ de ${formatCurrency(numericAmount)} processado para ${company.name}`,
            data: {
                companyId,
                newBalance: company.currentBalance,
                withdrawnAmount: numericAmount
            }
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to process CNPJ withdrawal'
        });
    }
});

// ============================================================================
// YIELD HISTORY ENDPOINTS
// ============================================================================

// Get yield history for a company
app.get('/api/pool/companies/:id/yield-history', async (req: Request, res: Response) => {
    try {
        const { id } = req.params;
        const { period = '30d' } = req.query;
        
        const companies = generateMockPoolCompanies(500);
        const company = companies.find(c => c.id === id);
        
        if (!company) {
            return res.status(404).json({
                status: 'error',
                message: 'Company not found'
            });
        }
        
        // Generate yield history based on period
        const history = generateYieldHistory(company, period as string);
        
        res.json({
            status: 'success',
            data: history,
            period
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Failed to retrieve yield history'
        });
    }
});

// ============================================================================
// PORT SERVICE PROXY
// ============================================================================

// Proxy to Port Service
app.use('/api/port', async (req: Request, res: Response, next: NextFunction) => {
    try {
        const path = req.path.replace('/api/port', '');
        const method = req.method.toLowerCase();
        
        // Forward request to port service
        const response = await serviceClients.port.request({
            method: req.method,
            url: path,
            data: req.body,
            params: req.query,
            headers: {
                ...req.headers,
                host: undefined,
                'content-length': undefined
            }
        });
        
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error instanceof AxiosError) {
            res.status(error.response?.status || 500).json(error.response?.data || { status: 'error', message: error.message });
        } else {
            res.status(500).json({ status: 'error', message: 'Port service unavailable' });
        }
    }
});

// ============================================================================
// QUANTUM SERVICE PROXY
// ============================================================================

// Proxy to Quantum Service
app.use('/api/quantum', async (req: Request, res: Response, next: NextFunction) => {
    try {
        const path = req.path.replace('/api/quantum', '');
        
        const response = await serviceClients.quantum.request({
            method: req.method,
            url: path,
            data: req.body,
            params: req.query
        });
        
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error instanceof AxiosError) {
            res.status(error.response?.status || 500).json(error.response?.data || { status: 'error', message: error.message });
        } else {
            res.status(500).json({ status: 'error', message: 'Quantum service unavailable' });
        }
    }
});

// ============================================================================
// HFT SERVICE PROXY
// ============================================================================

// Proxy to HFT Service
app.use('/api/hft', async (req: Request, res: Response, next: NextFunction) => {
    try {
        const path = req.path.replace('/api/hft', '');
        
        const response = await serviceClients.hft.request({
            method: req.method,
            url: path,
            data: req.body,
            params: req.query
        });
        
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error instanceof AxiosError) {
            res.status(error.response?.status || 500).json(error.response?.data || { status: 'error', message: error.message });
        } else {
            res.status(500).json({ status: 'error', message: 'HFT service unavailable' });
        }
    }
});

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Generate mock pool companies
 */
function generateMockPoolCompanies(count: number = 500): any[] {
    const POOL_SEGMENTS = [
        'Agro Sustentável', 'Biodiversidade', 'Energia Renovável', 'Logística', 
        'Captura de Carbono', 'Conservação', 'Saneamento', 'Mineração Verde', 
        'Energia Solar', 'Varejo Sustentável', 'Agrofloresta', 'Reflorestamento', 
        'Reciclagem', 'Bioenergia', 'Aquicultura', 'Turismo Ecológico', 
        'Construção Verde', 'Mobilidade Elétrica', 'Saúde Ambiental', 'Tecnologia Limpa'
    ];
    const REGIONS = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'];
    const prefixes = ['Agro', 'Bio', 'Eco', 'Terra', 'Verde', 'Solar', 'Hydro', 'Geo', 'Neo', 'Urbano'];
    const suffixes = ['Verde S.A.', 'Tech', 'Farms', 'Brasil', 'Sustainability', 'Corp', 'Group', 'Holdings'];
    const ratingPool = ['A+', 'A+', 'A', 'A', 'A-', 'B+', 'B+', 'B', 'B-', 'C+'];
    
    const companies: any[] = [];
    const usedIds = new Set<string>();
    const usedNames = new Set<string>();
    
    const nextId = (): string => {
        let id: string;
        do {
            id = '#' + Math.floor(100000 + Math.random() * 900000);
        } while (usedIds.has(id));
        usedIds.add(id);
        return id;
    };
    
    // Add some well-known companies
    const originals = [
        { name: 'AgroVerde S.A.', segment: 'Agro Sustentável', contribution: 48200000000, baseYield: 12.4, audit: 'B2G-OK', rating: 'A+' },
        { name: 'BioToken Amazônia', segment: 'Biodiversidade', contribution: 32400000000, baseYield: 15.8, audit: 'B2G-OK', rating: 'A' },
        { name: 'CarbonCapture BR', segment: 'Captura de Carbono', contribution: 61200000000, baseYield: 18.3, audit: 'B2G-OK', rating: 'A+' },
        { name: 'EcoMineração Ltda', segment: 'Mineração Verde', contribution: 28700000000, baseYield: 13.6, audit: 'B2G-OK', rating: 'A' },
        { name: 'SolarNordeste S.A.', segment: 'Energia Solar', contribution: 37500000000, baseYield: 10.8, audit: 'B2G-OK', rating: 'A' },
        { name: 'HidroClean Energia', segment: 'Energia Renovavel', contribution: 55000000000, baseYield: 14.2, audit: 'B2G-OK', rating: 'A+' }
    ];
    
    originals.forEach(o => {
        companies.push({
            id: nextId(),
            ...o,
            region: REGIONS[Math.floor(Math.random() * REGIONS.length)],
            currentBalance: o.contribution,
            earnings: 0,
            totalWithdrawn: 0,
            withdrawHistory: [],
            yieldHistory: [],
            yieldPct: o.baseYield,
            lastYield: o.baseYield,
            isFalencia: Math.random() > 0.85,
            falenciaContribution: Math.random() > 0.85 ? o.contribution * 0.2 : 0
        });
        usedNames.add(o.name);
    });
    
    // Generate remaining companies
    while (companies.length < count) {
        const p = prefixes[Math.floor(Math.random() * prefixes.length)];
        const s = suffixes[Math.floor(Math.random() * suffixes.length)];
        const seg = POOL_SEGMENTS[Math.floor(Math.random() * POOL_SEGMENTS.length)];
        const name = `${p} ${s}`;
        
        if (usedNames.has(name)) continue;
        usedNames.add(name);
        
        const contribution = Math.floor(5000000000 + Math.random() * 85000000000);
        const baseYield = parseFloat((5 + Math.random() * 14).toFixed(1));
        const audit = Math.random() > 0.25 ? 'B2G-OK' : 'B2G-PEND';
        const rating = ratingPool[Math.floor(Math.random() * ratingPool.length)];
        const region = REGIONS[Math.floor(Math.random() * REGIONS.length)];
        const isFalencia = Math.random() > 0.85;
        const falenciaContribution = isFalencia ? contribution * 0.2 : 0;
        
        companies.push({
            id: nextId(),
            name,
            segment: seg,
            contribution,
            baseYield,
            audit,
            rating,
            region,
            currentBalance: contribution + (isFalencia ? falenciaContribution : 0),
            earnings: 0,
            totalWithdrawn: 0,
            withdrawHistory: [],
            yieldHistory: [],
            yieldPct: baseYield,
            lastYield: baseYield,
            isFalencia,
            falenciaContribution
        });
    }
    
    return companies;
}

/**
 * Check if user has withdrawal permission
 */
async function checkWithdrawPermission(userId: string): Promise<boolean> {
    // Mock implementation - in production, check against B2G authorization service
    const authorizedUsers = ['kaue.caires', 'auditor.b2g', 'admin.simea'];
    return authorizedUsers.includes(userId.toLowerCase());
}

/**
 * Verify B2G audit code
 */
async function verifyB2GAuditCode(auditCode: string, companyId: string, userId: string): Promise<boolean> {
    // Mock implementation - in production, verify with B2G audit service
    // For demo purposes, accept any non-empty code
    return !!auditCode && auditCode.length >= 10;
}

/**
 * Log B2G audit transaction
 */
async function logB2GAudit(auditData: any): Promise<void> {
    // Mock implementation - in production, send to B2G audit logging service
    console.log('B2G Audit Log:', auditData);
}

/**
 * Calculate daily yield for a company
 */
function calculateDailyYield(company: any): number {
    // Calculate based on current balance and yield percentage
    const dailyRate = company.yieldPct / 100 / 365;
    return company.currentBalance * dailyRate;
}

/**
 * Generate yield history for a company
 */
function generateYieldHistory(company: any, period: string): any {
    const now = Date.now();
    let startDate: Date;
    
    switch (period) {
        case '1h':
            startDate = new Date(now - 60 * 60 * 1000);
            break;
        case '24h':
            startDate = new Date(now - 24 * 60 * 60 * 1000);
            break;
        case '7d':
            startDate = new Date(now - 7 * 24 * 60 * 60 * 1000);
            break;
        case '30d':
            startDate = new Date(now - 30 * 24 * 60 * 60 * 1000);
            break;
        case 'total':
            startDate = new Date(company.yieldHistory?.[0]?.t || now - 30 * 24 * 60 * 60 * 1000);
            break;
        default:
            startDate = new Date(now - 24 * 60 * 60 * 1000);
    }
    
    // Generate mock yield history
    const history: any[] = [];
    const points = period === 'total' ? 100 : (period === '30d' ? 30 : (period === '7d' ? 7 : (period === '24h' ? 24 : 6)));
    
    for (let i = 0; i < points; i++) {
        const t = startDate.getTime() + (i * (now - startDate.getTime()) / points);
        const baseYield = company.baseYield || 10;
        const variation = (Math.random() - 0.5) * 2; // -1 to +1 percent
        const yieldPct = Math.max(0.1, baseYield + variation);
        const yieldValue = company.currentBalance * (yieldPct / 100) * (1 / 365);
        
        history.push({
            t,
            v: yieldValue,
            pct: yieldPct
        });
    }
    
    return {
        yields: history,
        totalRendered: history.reduce((sum, h) => sum + h.v, 0),
        avgYieldPct: history.reduce((sum, h) => sum + h.pct, 0) / history.length
    };
}

/**
 * Format currency
 */
function formatCurrency(amount: number): string {
    if (amount >= 1e12) return 'R$ ' + (amount / 1e12).toFixed(4).replace('.', ',') + ' tri';
    if (amount >= 1e9) return 'R$ ' + (amount / 1e9).toFixed(4).replace('.', ',') + ' bi';
    if (amount >= 1e6) return 'R$ ' + (amount / 1e6).toFixed(2).replace('.', ',') + ' mi';
    if (amount >= 1e3) return 'R$ ' + (amount / 1e3).toFixed(2).replace('.', ',') + ' mil';
    return 'R$ ' + amount.toFixed(2).replace('.', ',');
}

// ============================================================================
// START SERVER
// ============================================================================

app.listen(PORT, () => {
    console.log(`✓ SIMEA API Gateway running on port ${PORT}`);
    console.log(`✓ Health check: http://localhost:${PORT}/api/health`);
    console.log(`✓ Pool companies: http://localhost:${PORT}/api/pool/companies`);
    console.log(`✓ Port service: http://localhost:${PORT}/api/port/ports`);
});

export default app;
