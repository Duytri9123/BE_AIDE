using System;
using System.IO;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;
public class ExportSupplierStates {
 [CommandMethod("AIDEEXPORTSTATES")]
 public void Run(){
  var source=Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument.Database;
  foreach(var line in File.ReadAllLines(Environment.GetEnvironmentVariable("AIDE_STATE_JOBS"))){
   var parts=line.Split('\t');
   try{
    ObjectId id=source.GetObjectId(false,new Handle(Convert.ToInt64(parts[0],16)),0);
    using(var target=new Database(true,true)){
     var map=new IdMapping();source.WblockCloneObjects(new ObjectIdCollection(new[]{id}),target.CurrentSpaceId,map,DuplicateRecordCloning.Replace,false);
     using(var tx=target.TransactionManager.StartTransaction()){
      var br=(BlockReference)tx.GetObject(map[id].Value,OpenMode.ForWrite);
      if(!br.IsDynamicBlock)throw new System.Exception("Not a dynamic reference");
      bool found=false;
      foreach(DynamicBlockReferenceProperty prop in br.DynamicBlockReferencePropertyCollection){
       if(prop.PropertyName!="Options")continue;
       foreach(var allowed in prop.GetAllowedValues())if(Convert.ToString(allowed)==parts[1]){prop.Value=allowed;found=true;break;}
      }
      if(!found)throw new System.Exception("Source option missing: "+parts[1]);
      // Options and Poles are separate lookup properties in supplier blocks.
      // Leaving Poles at the original 3P/f can export a mixed 4P state.
      var match=System.Text.RegularExpressions.Regex.Match(parts[1],@"^([1-4]P):.*?(Front|Cover)",System.Text.RegularExpressions.RegexOptions.IgnoreCase);
      string wanted=match.Success?match.Groups[1].Value+"/"+(match.Groups[2].Value.Equals("Front",StringComparison.OrdinalIgnoreCase)?"f":"c"):"None";
      foreach(DynamicBlockReferenceProperty prop in br.DynamicBlockReferencePropertyCollection){
       if(!prop.PropertyName.Equals("Poles",StringComparison.OrdinalIgnoreCase))continue;
       bool poleFound=false;
       foreach(var allowed in prop.GetAllowedValues())if(string.Equals(Convert.ToString(allowed),wanted,StringComparison.OrdinalIgnoreCase)){prop.Value=allowed;poleFound=true;break;}
       if(!poleFound)throw new System.Exception("Source pole state missing: "+wanted);
      }
      var block=(BlockTableRecord)tx.GetObject(br.DynamicBlockTableRecord,OpenMode.ForWrite);block.UpdateAnonymousBlocks();
      tx.Commit();
     }
     target.DxfOut(parts[2],16,DwgVersion.AC1032);
     File.WriteAllText(parts[2]+".ok",parts[1]);
    }
   }catch(System.Exception e){File.WriteAllText(parts[2]+".error",e.ToString());}
  }
 }
}

