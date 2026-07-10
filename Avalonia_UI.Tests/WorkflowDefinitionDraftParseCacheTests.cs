using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftParseCacheTests
{
    [TestMethod]
    public void CacheReusesParsersForSameDraftJson()
    {
        var parseCalls = 0;
        var structureCalls = 0;
        var linearCalls = 0;
        var runtimeCalls = 0;
        var loopCalls = 0;
        var cache = new WorkflowDefinitionDraftParseCache(
            json =>
            {
                parseCalls++;
                return WorkflowDefinitionDraftSnapshot.Parse(json);
            },
            (_, _) =>
            {
                structureCalls++;
                return new WorkflowDefinitionDraftStructure
                {
                    Status = WorkflowDefinitionDraftStructureStatus.Supported,
                };
            },
            _ =>
            {
                linearCalls++;
                return WorkflowDefinitionLinearChainAnalysis.Linear(["node-1"]);
            },
            _ =>
            {
                runtimeCalls++;
                return new RuntimeOptionsDraftReadResult
                {
                    Status = RuntimeOptionsDraftReadStatus.Succeeded,
                    Draft = new RuntimeOptionsDraft(),
                };
            },
            _ =>
            {
                loopCalls++;
                return new WorkflowLoopRegionDraftReadResult
                {
                    Status = WorkflowLoopRegionDraftReadStatus.Succeeded,
                };
            });

        const string draftJson = """{"nodes":[],"connections":[]}""";
        var firstSnapshot = cache.GetSnapshot(draftJson);
        var secondSnapshot = cache.GetSnapshot(draftJson);
        var firstStructure = cache.GetStructure(draftJson);
        var secondStructure = cache.GetStructure(draftJson);
        var firstLinear = cache.GetLinearChainAnalysis(draftJson);
        var secondLinear = cache.GetLinearChainAnalysis(draftJson);
        var firstRuntime = cache.GetRuntimeOptions(draftJson);
        var secondRuntime = cache.GetRuntimeOptions(draftJson);
        var firstLoops = cache.GetLoopRegions(draftJson);
        var secondLoops = cache.GetLoopRegions(draftJson);

        Assert.AreSame(firstSnapshot, secondSnapshot);
        Assert.AreSame(firstStructure, secondStructure);
        Assert.AreSame(firstLinear, secondLinear);
        Assert.AreSame(firstRuntime, secondRuntime);
        Assert.AreSame(firstLoops, secondLoops);
        Assert.AreEqual(1, parseCalls);
        Assert.AreEqual(1, structureCalls);
        Assert.AreEqual(1, linearCalls);
        Assert.AreEqual(1, runtimeCalls);
        Assert.AreEqual(1, loopCalls);
    }

    [TestMethod]
    public void CacheInvalidatesWhenDraftJsonChangesOrIsExplicitlyInvalidated()
    {
        var structureCalls = 0;
        var parseCalls = 0;
        var cache = new WorkflowDefinitionDraftParseCache(
            json =>
            {
                parseCalls++;
                return WorkflowDefinitionDraftSnapshot.Parse(json);
            },
            (_, _) =>
            {
                structureCalls++;
                return new WorkflowDefinitionDraftStructure
                {
                    Status = WorkflowDefinitionDraftStructureStatus.Supported,
                    Warnings = [$"build-{structureCalls}"],
                };
            },
            _ => WorkflowDefinitionLinearChainAnalysis.Linear([]),
            _ => new RuntimeOptionsDraftReadResult
            {
                Status = RuntimeOptionsDraftReadStatus.Succeeded,
                Draft = new RuntimeOptionsDraft(),
            },
            _ => new WorkflowLoopRegionDraftReadResult
            {
                Status = WorkflowLoopRegionDraftReadStatus.Succeeded,
            });

        var first = cache.GetStructure("""{"nodes":[],"connections":[]}""");
        var second = cache.GetStructure("""{"nodes":[{}],"connections":[]}""");
        cache.Invalidate();
        var third = cache.GetStructure("""{"nodes":[{}],"connections":[]}""");

        Assert.AreEqual(3, structureCalls);
        Assert.AreEqual(3, parseCalls);
        Assert.AreEqual("build-1", first?.Warnings[0]);
        Assert.AreEqual("build-2", second?.Warnings[0]);
        Assert.AreEqual("build-3", third?.Warnings[0]);
    }

    [TestMethod]
    public void BlankDraftDoesNotInvokeParsers()
    {
        var parserCalled = false;
        var cache = new WorkflowDefinitionDraftParseCache(
            _ =>
            {
                parserCalled = true;
                return WorkflowDefinitionDraftSnapshot.Parse("{}");
            },
            (_, _) =>
            {
                parserCalled = true;
                return new WorkflowDefinitionDraftStructure();
            },
            _ =>
            {
                parserCalled = true;
                return WorkflowDefinitionLinearChainAnalysis.Rejected("unexpected");
            },
            _ =>
            {
                parserCalled = true;
                return new RuntimeOptionsDraftReadResult
                {
                    Status = RuntimeOptionsDraftReadStatus.JsonInvalid,
                };
            },
            _ =>
            {
                parserCalled = true;
                return new WorkflowLoopRegionDraftReadResult
                {
                    Status = WorkflowLoopRegionDraftReadStatus.JsonInvalid,
                };
            });

        Assert.IsNull(cache.GetSnapshot(" "));
        Assert.IsNull(cache.GetStructure(" "));
        Assert.IsNull(cache.GetLinearChainAnalysis(" "));
        Assert.IsTrue(cache.GetRuntimeOptions(" ").Succeeded);
        Assert.IsTrue(cache.GetLoopRegions(" ").Succeeded);
        Assert.IsFalse(parserCalled);
    }
}
