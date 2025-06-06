// Domain Entity: User - Migrated from existing types/auth.ts
import { UserProfile, SubscriptionTier } from '../../types/auth';

export interface UserData {
  readonly id: string;
  readonly userId: string;
  readonly email: string;
  readonly username?: string;
  readonly fullName?: string;
  readonly avatarUrl?: string;
  readonly bio?: string;
  readonly subscriptionTier: SubscriptionTier;
  readonly isActive: boolean;
  readonly isVerified: boolean;
  readonly createdAt: Date;
  readonly lastLoginAt?: Date;
}

export class User implements UserData {
  constructor(
    public readonly id: string,
    public readonly userId: string,
    public readonly email: string,
    public readonly username: string | undefined,
    public readonly fullName: string | undefined,
    public readonly avatarUrl: string | undefined,
    public readonly bio: string | undefined,
    public readonly subscriptionTier: SubscriptionTier,
    public readonly isActive: boolean,
    public readonly isVerified: boolean,
    public readonly createdAt: Date,
    public readonly lastLoginAt?: Date
  ) {}

  // Factory method from existing UserProfile
  static fromProfile(profile: UserProfile): User {
    return new User(
      profile.id.toString(),
      profile.user_id,
      profile.email,
      profile.username,
      profile.full_name,
      profile.avatar_url,
      profile.bio,
      profile.subscription_tier,
      profile.is_active,
      profile.is_verified,
      new Date(profile.created_at),
      profile.last_login_at ? new Date(profile.last_login_at) : undefined
    );
  }

  // Factory method for creating new users
  static create(data: {
    email: string;
    fullName?: string;
    username?: string;
    subscriptionTier?: SubscriptionTier;
  }): User {
    const id = crypto.randomUUID();
    const userId = crypto.randomUUID();
    const now = new Date();
    
    // Business rules
    if (!data.email || !data.email.includes('@')) {
      throw new Error('Valid email is required');
    }

    if (data.username && data.username.length < 3) {
      throw new Error('Username must be at least 3 characters');
    }

    return new User(
      id,
      userId,
      data.email.toLowerCase(),
      data.username,
      data.fullName,
      undefined,
      undefined,
      data.subscriptionTier || 'free',
      true,
      false,
      now,
      undefined
    );
  }

  // Domain business methods
  isPremium(): boolean {
    return this.subscriptionTier === 'pro' || this.subscriptionTier === 'enterprise';
  }

  isFree(): boolean {
    return this.subscriptionTier === 'free';
  }

  canAccessPremiumFeatures(): boolean {
    return this.isPremium() && this.isActive && this.isVerified;
  }

  needsVerification(): boolean {
    return !this.isVerified;
  }

  hasAvatar(): boolean {
    return !!this.avatarUrl;
  }

  getDisplayName(): string {
    return this.fullName || this.username || this.email.split('@')[0];
  }

  getInitials(): string {
    const name = this.getDisplayName();
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  isRecentlyActive(): boolean {
    if (!this.lastLoginAt) return false;
    const daysSinceLogin = (Date.now() - this.lastLoginAt.getTime()) / (1000 * 60 * 60 * 24);
    return daysSinceLogin <= 7;
  }

  // Usage quota based on subscription tier
  getMessageQuota(): { total: number; resetPeriod: 'day' | 'month' } {
    switch (this.subscriptionTier) {
      case 'free':
        return { total: 20, resetPeriod: 'day' };
      case 'pro':
        return { total: 1000, resetPeriod: 'month' };
      case 'enterprise':
        return { total: 10000, resetPeriod: 'month' };
      default:
        return { total: 20, resetPeriod: 'day' };
    }
  }

  // Convert to backend UserProfile format
  toProfile(): UserProfile {
    return {
      id: parseInt(this.id),
      user_id: this.userId,
      email: this.email,
      username: this.username,
      full_name: this.fullName,
      avatar_url: this.avatarUrl,
      bio: this.bio,
      subscription_tier: this.subscriptionTier,
      is_active: this.isActive,
      is_verified: this.isVerified,
      created_at: this.createdAt.toISOString(),
      last_login_at: this.lastLoginAt?.toISOString(),
    };
  }

  // Update user data (immutable)
  update(data: Partial<{
    fullName: string;
    username: string;
    bio: string;
    avatarUrl: string;
  }>): User {
    return new User(
      this.id,
      this.userId,
      this.email,
      data.username ?? this.username,
      data.fullName ?? this.fullName,
      data.avatarUrl ?? this.avatarUrl,
      data.bio ?? this.bio,
      this.subscriptionTier,
      this.isActive,
      this.isVerified,
      this.createdAt,
      this.lastLoginAt
    );
  }

  // Mark as verified
  markAsVerified(): User {
    return new User(
      this.id,
      this.userId,
      this.email,
      this.username,
      this.fullName,
      this.avatarUrl,
      this.bio,
      this.subscriptionTier,
      this.isActive,
      true,
      this.createdAt,
      this.lastLoginAt
    );
  }

  // Update last login
  updateLastLogin(): User {
    return new User(
      this.id,
      this.userId,
      this.email,
      this.username,
      this.fullName,
      this.avatarUrl,
      this.bio,
      this.subscriptionTier,
      this.isActive,
      this.isVerified,
      this.createdAt,
      new Date()
    );
  }
} 