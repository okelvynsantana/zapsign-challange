import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';

import { AuthService } from './core/auth/auth.service';
import { AppHeaderComponent } from './ui/organisms/app-header.component';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, AppHeaderComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  private readonly router = inject(Router);
  readonly auth = inject(AuthService);

  /** The shell owns the route change; the header only reports the intent. */
  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
