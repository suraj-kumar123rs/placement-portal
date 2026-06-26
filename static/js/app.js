const { createApp } = Vue;

createApp({
  data() {
    return {
      // Auth
      user: null,
      authTab: 'login',
      authError: '',
      authSuccess: '',
      loginForm: { email: '', password: '' },
      regForm: { role: 'student', email: '', password: '', name: '', branch: '', year: 1, cgpa: 0, phone: '', company_name: '', hr_contact: '', website: '', description: '' },

      // Toast
      toast: '',

      // Admin
      adminTab: 'companies',
      stats: {},
      adminCompanies: [],
      adminStudents: [],
      adminDrives: [],
      adminApplications: [],
      searchCompany: '',
      searchStudent: '',

      // Company
      coTab: 'drives',
      coDash: { company: {}, drives: [], total_applicants: 0 },
      driveForm: { job_title: '', job_description: '', required_branch: '', required_cgpa: '', required_year: '', deadline: '' },
      driveMsg: '',
      coApplications: [],
      coAppDriveFilter: '',

      // Student
      stTab: 'drives',
      stDash: { student: {}, drives: [], applications: [] },
      stBranchFilter: '',
      stCgpaFilter: '',
      profileForm: { name: '', branch: '', year: 1, cgpa: 0, phone: '' },
      profileMsg: ''
    };
  },

  async mounted() {
    await this.checkSession();
  },

  methods: {
    showToast(msg) {
      this.toast = msg;
      setTimeout(() => this.toast = '', 3000);
    },

    async api(url, method = 'GET', body = null) {
      const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(url, opts);
      return { ok: res.ok, status: res.status, data: await res.json() };
    },

    async checkSession() {
      const r = await this.api('/api/me');
      if (r.ok) {
        this.user = r.data;
        this.loadDashboard();
      }
    },

    async doLogin() {
      this.authError = '';
      const r = await this.api('/api/login', 'POST', this.loginForm);
      if (r.ok) {
        this.user = { email: r.data.email, role: r.data.role };
        this.loadDashboard();
      } else {
        this.authError = r.data.error || 'Login failed';
      }
    },

    async doRegister() {
      this.authError = '';
      this.authSuccess = '';
      const r = await this.api('/api/register', 'POST', this.regForm);
      if (r.ok) {
        this.authSuccess = r.data.message;
        this.authTab = 'login';
      } else {
        this.authError = r.data.error || 'Registration failed';
      }
    },

    async logout() {
      await this.api('/api/logout', 'POST');
      this.user = null;
      this.authTab = 'login';
      this.authError = '';
    },

    loadDashboard() {
      if (!this.user) return;
      if (this.user.role === 'admin') {
        this.loadAdminStats();
        this.loadAdminCompanies();
      } else if (this.user.role === 'company') {
        this.loadCoDash();
      } else if (this.user.role === 'student') {
        this.loadStudentDash();
      }
    },

    // ─── ADMIN ───
    async loadAdminStats() {
      const r = await this.api('/api/admin/dashboard');
      if (r.ok) this.stats = r.data;
    },

    async loadAdminCompanies() {
      const r = await this.api(`/api/admin/companies?search=${this.searchCompany}`);
      if (r.ok) this.adminCompanies = r.data;
    },

    async loadAdminStudents() {
      const r = await this.api(`/api/admin/students?search=${this.searchStudent}`);
      if (r.ok) this.adminStudents = r.data;
    },

    async loadAdminDrives() {
      const r = await this.api('/api/admin/drives');
      if (r.ok) this.adminDrives = r.data;
    },

    async loadAdminApplications() {
      const r = await this.api('/api/admin/applications');
      if (r.ok) this.adminApplications = r.data;
    },

    async approveCompany(id, action) {
      const r = await this.api(`/api/admin/companies/${id}/approve`, 'POST', { action });
      if (r.ok) { this.showToast(r.data.message); this.loadAdminCompanies(); this.loadAdminStats(); }
    },

    async blacklistCompany(id) {
      const r = await this.api(`/api/admin/companies/${id}/blacklist`, 'POST');
      if (r.ok) { this.showToast('Updated'); this.loadAdminCompanies(); }
    },

    async blacklistStudent(id) {
      const r = await this.api(`/api/admin/students/${id}/blacklist`, 'POST');
      if (r.ok) { this.showToast('Updated'); this.loadAdminStudents(); }
    },

    async approveDrive(id, action) {
      const r = await this.api(`/api/admin/drives/${id}/approve`, 'POST', { action });
      if (r.ok) { this.showToast(r.data.message); this.loadAdminDrives(); this.loadAdminStats(); }
    },

    // ─── COMPANY ───
    async loadCoDash() {
      const r = await this.api('/api/company/dashboard');
      if (r.ok) this.coDash = r.data;
    },

    async createDrive() {
      this.driveMsg = '';
      const r = await this.api('/api/company/drives', 'POST', this.driveForm);
      if (r.ok) {
        this.driveMsg = r.data.message;
        this.driveForm = { job_title: '', job_description: '', required_branch: '', required_cgpa: '', required_year: '', deadline: '' };
        this.loadCoDash();
      } else {
        this.driveMsg = r.data.error || 'Failed';
      }
    },

    async loadCoApplications() {
      const url = '/api/company/applications' + (this.coAppDriveFilter ? `?drive_id=${this.coAppDriveFilter}` : '');
      const r = await this.api(url);
      if (r.ok) this.coApplications = r.data;
    },

    async updateAppStatus(appId, status) {
      if (!status) return;
      const r = await this.api(`/api/company/applications/${appId}/status`, 'POST', { status });
      if (r.ok) { this.showToast('Status updated'); this.loadCoApplications(); }
    },

    // ─── STUDENT ───
    async loadStudentDash() {
      let url = '/api/student/dashboard';
      const params = [];
      if (this.stBranchFilter) params.push(`branch=${this.stBranchFilter}`);
      if (this.stCgpaFilter) params.push(`cgpa=${this.stCgpaFilter}`);
      if (params.length) url += '?' + params.join('&');
      const r = await this.api(url);
      if (r.ok) {
        this.stDash = r.data;
        if (r.data.student) {
          this.profileForm = { ...r.data.student };
        }
      }
    },

    async applyDrive(driveId) {
      const r = await this.api(`/api/student/apply/${driveId}`, 'POST');
      if (r.ok) { this.showToast(r.data.message); this.loadStudentDash(); }
      else { this.showToast(r.data.error || 'Error'); }
    },

    async saveProfile() {
      this.profileMsg = '';
      const r = await this.api('/api/student/profile', 'POST', this.profileForm);
      if (r.ok) { this.profileMsg = r.data.message; this.loadStudentDash(); }
      else { this.profileMsg = r.data.error || 'Failed'; }
    },

    // ─── HELPERS ───
    statusBadge(s) {
      return { 'bg-warning text-dark': s === 'Pending', 'bg-success': s === 'Approved', 'bg-danger': s === 'Rejected' || s === 'Closed' };
    },
    appStatusBadge(s) {
      return { 'bg-primary': s === 'Applied', 'bg-warning text-dark': s === 'Shortlisted', 'bg-success': s === 'Selected', 'bg-danger': s === 'Rejected' };
    }
  }
}).mount('#app');
