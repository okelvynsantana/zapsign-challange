import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { LoginComponent } from './core/auth/login.component';

export const routes: Routes = [
  { path: '', redirectTo: 'documents', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  {
    path: 'companies',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./companies/companies.component').then((m) => m.CompaniesComponent),
  },
  {
    path: 'documents',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./documents/documents.component').then((m) => m.DocumentsComponent),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadComponent: () => import('./reports/reports.component').then((m) => m.ReportsComponent),
  },
  {
    path: 'alerts',
    canActivate: [authGuard],
    loadComponent: () => import('./alerts/alerts.component').then((m) => m.AlertsComponent),
  },
  { path: '**', redirectTo: 'documents' },
];
