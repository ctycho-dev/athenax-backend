# Audit Form Management System

## Project Overview
The Audit Form system tracks and manages audit processes within the application. It maintains audit states, tracks user associations, records audit steps, and stores administrative comments. The system also automatically tracks creation and modification timestamps for audit records.

## Database Schema - AuditForm

| Field Name | Type | Required | Default Value | Description | Example |
|------------|------|----------|---------------|-------------|---------|
| **state** | ReportState | Yes | `ReportState.get_default()` | Current state of the audit report | "draft", "in_review", "approved" |
| **user** | Link[User] | No | `None` | Reference to the associated user | User object reference |
| **steps** | AuditSteps | Yes | - | Collection of audit steps and their statuses | Contains step completion data |
| **user_privy_id** | str | Yes | - | Unique identifier for the user in Privy system | "usr_123456789" |
| **admin_comment** | str | No | `None` | Administrator notes or feedback (max 1000 chars) | "Please verify section 3.2" |
| **created_at** | datetime | Yes | Current timestamp | When the audit was created | "2023-11-15T14:30:00Z" |
| **updated_at** | datetime | Yes | Current timestamp | When the audit was last updated | "2023-11-16T09:15:00Z" |

### Collection Details
- **Collection Name**: `user_audit`
- **Indexed Fields**: `user_privy_id`

### Key Features
1. **Automatic Timestamping**: Tracks both creation and last update times automatically
2. **State Management**: Built-in state machine for audit lifecycle management
3. **Administrative Notes**: Optional field for admin comments with length validation
4. **User Association**: Links to user records while maintaining Privy ID reference
5. **Audit Trail**: Detailed steps tracking through embedded AuditSteps structure

### Enum/Type References
- **ReportState**: Tracks audit progress (draft, in_review, approved, etc.)
- **AuditSteps**: Contains detailed step-by-step audit information
- **User**: Reference to the user model for associated user data