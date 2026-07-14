using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RuntimeStatusLocalizationTests
{
    [TestMethod]
    public async Task FormatterLocalizesSupportedStatusesAndKeepsUnknownValue()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var formatter = new DisplayTextFormatter(localizationService);
        var expected = new Dictionary<string, string>
        {
            ["PENDING"] = "等待中",
            ["READY"] = "已就绪",
            ["WAITING_DEPENDENCY"] = "等待依赖",
            ["QUEUED"] = "已排队",
            ["RUNNING"] = "运行中",
            ["LONG_RUNNING"] = "长时间运行中",
            ["CANCEL_REQUESTED"] = "正在请求取消",
            ["SUSPECTED_HUNG"] = "疑似无响应",
            ["TIMED_OUT"] = "已超时",
            ["SUCCEEDED"] = "已成功",
            ["FAILED"] = "已失败",
            ["CANCELLED"] = "已取消",
            ["SKIPPED"] = "已跳过",
            ["ABORTED"] = "已中止",
            ["ENDED"] = "已结束",
            ["MAX_ITERATIONS_REACHED"] = "已达到最大循环次数",
        };

        foreach (var pair in expected)
        {
            Assert.AreEqual(pair.Value, formatter.FormatRuntimeStatus(pair.Key));
        }

        Assert.AreEqual(
            "FUTURE_RUNTIME_STATE",
            formatter.FormatRuntimeStatus("FUTURE_RUNTIME_STATE"));
    }

    [TestMethod]
    public async Task RunItemsRefreshLocalizedStatusWithoutChangingRawStatus()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var formatter = new DisplayTextFormatter(localizationService);
        var workflowRun = new WorkflowRunListItemViewModel(
            new WorkflowRunDto
            {
                WorkflowRunId = "run-1",
                WorkflowId = "wf-1",
                Status = "RUNNING",
                RunMode = "full",
                TriggerSource = "manual",
            },
            localizationService.GetString,
            formatter);
        var nodeRun = new NodeRunListItemViewModel(
            new NodeRunDto
            {
                NodeRunId = "node-run-1",
                WorkflowRunId = "run-1",
                NodeInstanceId = "node-1",
                NodeType = "FilterRowsNode",
                Status = "RUNNING",
            },
            formatter);
        var loopRun = new LoopRunListItemViewModel(
            new LoopRunDto
            {
                LoopRunId = "loop-run-1",
                WorkflowRunId = "run-1",
                LoopId = "loop-1",
                StartNodeInstanceId = "start",
                JudgeNodeInstanceId = "judge",
                Status = "RUNNING",
            },
            formatter);
        var iteration = new LoopIterationListItemViewModel(
            new LoopIterationRunDto
            {
                LoopIterationId = "iteration-1",
                LoopRunId = "loop-run-1",
                Status = "RUNNING",
            },
            formatter);
        var iterationNode = new LoopIterationNodeListItemViewModel(
            new LoopIterationNodeRunDto
            {
                LoopIterationId = "iteration-1",
                NodeRunId = "iteration-node-run-1",
                NodeInstanceId = "body",
                Role = "BODY",
                NodeType = "FilterRowsNode",
                Status = "RUNNING",
            },
            formatter);

        Assert.AreEqual("运行中", workflowRun.StatusText);
        Assert.AreEqual("运行中", nodeRun.StatusText);
        Assert.AreEqual("运行中", loopRun.StatusText);
        Assert.AreEqual("运行中", iteration.StatusText);
        Assert.AreEqual("运行中", iterationNode.StatusText);

        await localizationService.SetLanguageAsync("en-US");
        workflowRun.RefreshLocalizedText();
        nodeRun.RefreshLocalizedText();
        loopRun.RefreshLocalizedText();
        iteration.RefreshLocalizedText();
        iterationNode.RefreshLocalizedText();

        Assert.AreEqual("RUNNING", workflowRun.Status);
        Assert.AreEqual("RUNNING", nodeRun.Status);
        Assert.AreEqual("RUNNING", loopRun.Status);
        Assert.AreEqual("RUNNING", iteration.Status);
        Assert.AreEqual("RUNNING", iterationNode.Status);
        Assert.AreEqual("Running", workflowRun.StatusText);
        Assert.AreEqual("Running", nodeRun.StatusText);
        Assert.AreEqual("Running", loopRun.StatusText);
        Assert.AreEqual("Running", iteration.StatusText);
        Assert.AreEqual("Running", iterationNode.StatusText);
    }
}
