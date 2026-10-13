using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;
public class PreviewRegions {
  [CommandMethod("AIDEPREVIEWREGIONS")]
  public void Run() {
    foreach(var line in System.IO.File.ReadAllLines(Environment.GetEnvironmentVariable("AIDE_PREVIEW_JOBS"))) {
      var paths=line.Split('\t'); Render(paths[0],paths[1]);
    }
  }
  private void Render(string input,string output) {
    using(var db=new Database(false,true)) {
      db.DxfIn(input,output+".log");
      int count=0;
      using(var tx=db.TransactionManager.StartTransaction()) {
        var table=(BlockTable)tx.GetObject(db.BlockTableId,OpenMode.ForRead);
        foreach(ObjectId blockId in table) {
          var block=(BlockTableRecord)tx.GetObject(blockId,OpenMode.ForRead);
          var ids=new List<ObjectId>(); foreach(ObjectId id in block) ids.Add(id);
          foreach(ObjectId id in ids) {
            var region=tx.GetObject(id,OpenMode.ForRead) as Region;
            if(region==null) continue;
            block.UpgradeOpen();
            AppendRegionEdges(region,block,tx,0);
            region.UpgradeOpen(); region.Erase(); count++;
          }
        }
        tx.Commit();
      }
      db.DxfOut(output,16,DwgVersion.AC1032);
      System.IO.File.WriteAllText(output+".count",count.ToString());
    }
  }
  private void AppendRegionEdges(Region region,BlockTableRecord block,Transaction tx,int depth) {
    if(depth>32)throw new System.Exception("REGION explosion did not reach primitive edges");
    var pieces=new DBObjectCollection();region.Explode(pieces);
    foreach(DBObject part in pieces) {
      var entity=part as Entity;
      if(entity==null){part.Dispose();continue;}
      entity.SetPropertiesFrom(region);entity.Visible=region.Visible;
      var nested=entity as Region;
      if(nested!=null){try{AppendRegionEdges(nested,block,tx,depth+1);}finally{nested.Dispose();}}
      else {block.AppendEntity(entity);tx.AddNewlyCreatedDBObject(entity,true);}
    }
  }
}
