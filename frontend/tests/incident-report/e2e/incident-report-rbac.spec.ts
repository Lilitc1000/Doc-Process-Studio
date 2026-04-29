import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginAs,
  loginViaApi,
  loginViaApiAs,
  addRateLimitWhitelist,
  registerUserViaApi,
  assignIncidentRoleViaApi,
  createIncidentReportViaApi,
  submitIncidentReportViaApi,
  approveIncidentReportViaApi,
  rejectIncidentReportViaApi,
  assignHandlerViaApi,
  closeIncidentReportViaApi,
  deleteIncidentReportViaApi,
  cleanupWorkerData,
} from '../../helpers';

test.describe('事故报告 RBAC 角色权限流程', () => {
  test.setTimeout(120_000);

  let workerPrefix: string;
  let adminToken: string;
  let reporterUserId: string;
  let verifierUserId: string;
  let handlerUserId: string;
  let viewerUserId: string;
  let REPORTER_USER: string;
  let VERIFIER_USER: string;
  let HANDLER_USER: string;
  let VIEWER_USER: string;
  const TEST_PASS = 'Test1234!';

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    REPORTER_USER = `${workerPrefix}reporter`;
    VERIFIER_USER = `${workerPrefix}verifier`;
    HANDLER_USER = `${workerPrefix}handler`;
    VIEWER_USER = `${workerPrefix}viewer`;

    await addRateLimitWhitelist(request);
    await cleanupWorkerData(request, workerPrefix);
    adminToken = (await loginViaApi(request))!;

    const reporter = await registerUserViaApi(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifier = await registerUserViaApi(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );
    const handler = await registerUserViaApi(request, HANDLER_USER, TEST_PASS);
    const viewer = await registerUserViaApi(request, VIEWER_USER, TEST_PASS);

    expect(reporter, `注册用户 ${REPORTER_USER} 失败`).not.toBeNull();
    expect(verifier, `注册用户 ${VERIFIER_USER} 失败`).not.toBeNull();
    expect(handler, `注册用户 ${HANDLER_USER} 失败`).not.toBeNull();
    expect(viewer, `注册用户 ${VIEWER_USER} 失败`).not.toBeNull();

    reporterUserId = reporter!.user_id;
    verifierUserId = verifier!.user_id;
    handlerUserId = handler!.user_id;
    viewerUserId = viewer!.user_id;

    await assignIncidentRoleViaApi(
      request,
      adminToken,
      reporterUserId,
      'reporter',
    );
    await assignIncidentRoleViaApi(
      request,
      adminToken,
      verifierUserId,
      'verifier',
    );
    await assignIncidentRoleViaApi(
      request,
      adminToken,
      handlerUserId,
      'handler',
    );
    await assignIncidentRoleViaApi(request, adminToken, viewerUserId, 'viewer');
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });

  test('报告人可以创建并提交报告', async ({ request }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    expect(reporterToken).not.toBeNull();

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}报告人创建测试`,
    });
    expect(report).not.toBeNull();
    expect(report!.status).toBe('draft');

    const submitted = await submitIncidentReportViaApi(
      request,
      reporterToken!,
      report!.id,
    );
    expect(submitted).not.toBeNull();
    expect(submitted!.status).toBe('pending');

    await deleteIncidentReportViaApi(request, adminToken, report!.id);
  });

  test('审核人可以审核待审核报告', async ({ request }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifierToken = await loginViaApiAs(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}审核人审核测试`,
      severity: 'P1',
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, reporterToken!, report!.id);

    const approved = await approveIncidentReportViaApi(
      request,
      verifierToken!,
      report!.id,
      'E2E审核通过',
    );
    expect(approved).not.toBeNull();
    expect(approved!.status).toBe('approved');

    await deleteIncidentReportViaApi(request, adminToken, report!.id);
  });

  test('审核人可以驳回报告', async ({ request }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifierToken = await loginViaApiAs(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}审核人驳回测试`,
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, reporterToken!, report!.id);

    const rejected = await rejectIncidentReportViaApi(
      request,
      verifierToken!,
      report!.id,
      'E2E驳回原因',
    );
    expect(rejected).not.toBeNull();
    expect(rejected!.status).toBe('rejected');

    await deleteIncidentReportViaApi(request, adminToken, report!.id);
  });

  test('完整流程：创建→提交→审核→分配→关闭', async ({ request }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifierToken = await loginViaApiAs(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}完整流程测试`,
      severity: 'P0',
    });
    expect(report).not.toBeNull();
    expect(report!.status).toBe('draft');

    const submitted = await submitIncidentReportViaApi(
      request,
      reporterToken!,
      report!.id,
    );
    expect(submitted).not.toBeNull();
    expect(submitted!.status).toBe('pending');

    const approved = await approveIncidentReportViaApi(
      request,
      verifierToken!,
      report!.id,
      'E2E审核通过，开始处理',
    );
    expect(approved).not.toBeNull();
    expect(approved!.status).toBe('approved');

    const assigned = await assignHandlerViaApi(
      request,
      verifierToken!,
      report!.id,
      handlerUserId,
    );
    expect(assigned).not.toBeNull();
    expect(assigned!.status).toBe('in_progress');

    const handlerToken = await loginViaApiAs(request, HANDLER_USER, TEST_PASS);
    const closed = await closeIncidentReportViaApi(
      request,
      handlerToken!,
      report!.id,
      'E2E处理完成，关闭报告',
    );
    expect(closed).not.toBeNull();
    expect(closed!.status).toBe('closed');

    await deleteIncidentReportViaApi(request, adminToken, report!.id);
  });

  test('报告人可以在详情页看到编辑按钮（草稿状态）', async ({
    page,
    request,
  }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}草稿编辑按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await loginAs(page, REPORTER_USER, TEST_PASS);
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      await expect(editBtn).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, adminToken, report!.id);
    }
  });

  test('审核人可以在待审核报告详情页看到审核按钮', async ({
    page,
    request,
  }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}审核按钮可见性测试`,
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, reporterToken!, report!.id);

    try {
      await loginAs(page, VERIFIER_USER, TEST_PASS);
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      await expect(auditBtn).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, adminToken, report!.id);
    }
  });

  test('处理人可以在处理中报告详情页看到关闭按钮', async ({
    page,
    request,
  }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifierToken = await loginViaApiAs(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}关闭按钮可见性测试`,
      severity: 'P1',
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, reporterToken!, report!.id);
    await approveIncidentReportViaApi(
      request,
      verifierToken!,
      report!.id,
      '审核通过',
    );
    await assignHandlerViaApi(
      request,
      verifierToken!,
      report!.id,
      handlerUserId,
    );

    try {
      await loginAs(page, HANDLER_USER, TEST_PASS);
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const closeBtn = page.locator('.detail-header-right button', {
        hasText: '关闭',
      });
      await expect(closeBtn).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, adminToken, report!.id);
    }
  });

  test('管理员可以在已关闭报告详情页看到重新打开按钮', async ({
    page,
    request,
  }) => {
    const reporterToken = await loginViaApiAs(
      request,
      REPORTER_USER,
      TEST_PASS,
    );
    const verifierToken = await loginViaApiAs(
      request,
      VERIFIER_USER,
      TEST_PASS,
    );
    const handlerToken = await loginViaApiAs(request, HANDLER_USER, TEST_PASS);

    const report = await createIncidentReportViaApi(request, reporterToken!, {
      title: `${workerPrefix}重新打开按钮测试`,
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, reporterToken!, report!.id);
    await approveIncidentReportViaApi(
      request,
      verifierToken!,
      report!.id,
      '审核通过',
    );
    await assignHandlerViaApi(
      request,
      verifierToken!,
      report!.id,
      handlerUserId,
    );
    await closeIncidentReportViaApi(
      request,
      handlerToken!,
      report!.id,
      '处理完成',
    );

    try {
      await loginAsAdmin(page);
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const reopenBtn = page.locator('.detail-header-right button', {
        hasText: '重新打开',
      });
      await expect(reopenBtn).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, adminToken, report!.id);
    }
  });
});
